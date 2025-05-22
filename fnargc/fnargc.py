#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

from clang.cindex import (
    CompilationDatabase,
    CompilationDatabaseError,
    CursorKind,
    Diagnostic,
    Index,
    TranslationUnit,
    TranslationUnitLoadError,
)


def get_fn_name(cursor) -> str:
    result = ""

    kinds = [
        CursorKind.NAMESPACE,
        CursorKind.CLASS_DECL,
        CursorKind.CLASS_TEMPLATE,
        CursorKind.STRUCT_DECL,
    ]

    t = cursor.semantic_parent
    while True:
        if t.kind not in kinds:
            break
        result = str(t.spelling) + "::" + result
        t = t.semantic_parent

    result += str(cursor.spelling)

    return result


# parse the output of `cc -E -v -x c++ /dev/null` to get system include paths
def args_from_driver_output(output):
    r = []
    inc_list_started = False
    for line in output.splitlines():
        line = line.strip(" ").strip("\t")
        if line == "":
            continue
        if line.startswith("Target"):
            target = line.split(":")[1]
            r.append("--target=" + target.strip(" "))
        if line == "#include <...> search starts here:":
            inc_list_started = True
            continue
        if line == "End of search list.":
            inc_list_started = False
            continue
        if inc_list_started:
            r.append("-isystem")
            r.append(line)
    return r


def argv_from_compdb(directory, arguments) -> [str]:
    argv = []
    for a in arguments:
        if a == "-fno-aggressive-loop-optimizations":
            continue
        if a == "-Werror":
            continue
        if a.startswith("-I"):
            # make relative -I into absolute
            ipath = a[2:]
            if not os.path.isabs(ipath):
                ipath = os.path.normpath(os.path.join(directory, ipath))
                argv.append("-I" + ipath)
            else:
                argv.append(a)
        elif a.startswith("-o"):
            # -w inhibits all warning messages
            argv.append("-w")
            argv.append("-ferror-limit=0")
            argv.append(a)
        else:
            argv.append(a)

    if len(argv) == 0:
        raise RuntimeError("argv is empty")

    driver = argv[0]

    result = subprocess.run(
        [driver, "-E", "-v", "-x", "c++", "/dev/null"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if result.returncode != 0:
        print("returncode:", result.returncode)
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        raise RuntimeError("failed to run driver")

    argv.extend(args_from_driver_output(result.stdout))

    return argv


class Arg:
    def __init__(self, name: str, type: str):
        self.name = name
        self.type = type

    def __eq__(self, other):
        if not isinstance(other, Arg):
            return NotImplemented
        return self.name == other.name and self.type == other.type


class Func:
    def __init__(self, name: str, args: [Arg], return_type: str, file: str, line: int):
        self.name = name
        self.args = args
        self.return_type = return_type
        self.file = file
        self.line = line

    def __eq__(self, other):
        if not isinstance(other, Func):
            return NotImplemented
        return (
            self.name == other.name
            and self.args == self.args
            and self.return_type == other.return_type
        )


def is_in_src_paths(src_paths: [str], filename: str) -> bool:
    for src_path in src_paths:
        if filename.startswith(src_path):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Count function arguments.",
    )
    parser.add_argument(
        "-r",
        "--root-dir",
        help="Project root path",
        required=True,
    )
    parser.add_argument(
        "-b",
        "--build-dir",
        help="Path to build directory, relative to -r",
        default="build",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        help="Path to output file",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--src-dir",
        help="Path to src directory(ies)",
        action="append",
        required=True,
    )

    args = parser.parse_args()

    args.root_dir = os.path.abspath(args.root_dir)
    args.build_dir = os.path.abspath(os.path.join(args.root_dir, args.build_dir))

    srcs = []
    for s in args.src_dir:
        srcs.append(os.path.normpath(os.path.join(args.root_dir, s)))
    args.src_dir = srcs

    try:
        comp_db = CompilationDatabase.fromDirectory(args.build_dir)
    except CompilationDatabaseError:
        print('error loading compilation database from "%s"' % args.build_dir)
        sys.exit(1)

    index = Index.create()

    compile_commands = [
        v
        for v in comp_db.getAllCompileCommands()
        if v.filename.startswith(args.root_dir)
    ]

    funcs = []

    len_last_file = 0

    for i in range(len(compile_commands)):
        v = compile_commands[i]

        rel_file_path = v.filename.removeprefix(args.root_dir)
        extra = ""
        if len(rel_file_path) < len_last_file:
            extra = " " * (len_last_file - len(rel_file_path))
        print(f"[{i + 1}/{len(compile_commands)}] {rel_file_path}{extra}\r", end="")
        len_last_file = len(rel_file_path)

        argv = argv_from_compdb(v.directory, v.arguments)

        parse_options = TranslationUnit.PARSE_SKIP_FUNCTION_BODIES

        try:
            tu = index.parse(
                None,
                args=argv[1:],
                options=parse_options,
            )
        except TranslationUnitLoadError:
            print("\nerror parsing translation unit")
            sys.exit(1)

        should_exit = False
        for diag in tu.diagnostics:
            print(f"\n{diag}")
            if diag.severity == Diagnostic.Fatal or diag.severity == Diagnostic.Error:
                should_exit = True
        if should_exit:
            sys.exit(1)

        kinds = [
            CursorKind.CONSTRUCTOR,
            CursorKind.CXX_METHOD,
            CursorKind.FUNCTION_DECL,
            CursorKind.FUNCTION_TEMPLATE,
        ]

        for c in tu.cursor.walk_preorder():
            if not is_in_src_paths(args.src_dir, str(c.location.file)):
                continue

            if c.kind not in kinds:
                continue

            fn_args = [str]
            for arg in c.get_arguments():
                fn_args.append(
                    Arg(
                        name=str(arg.spelling),
                        type=str(arg.type.spelling),
                    )
                )

            fn = Func(
                name=get_fn_name(c),
                args=fn_args,
                return_type=str(c.result_type.spelling),
                file=str(c.location.file),
                line=int(c.location.line),
            )

            dup = fn in funcs
            if not dup:
                funcs.append(fn)

            # print(fn.file, fn.line, dup, fn.name)

    print("")

    with open(args.output_file, "w") as f:
        for fn in funcs:
            f.write(f"{fn.name},{len(fn.args)}\n")


if __name__ == "__main__":
    main()
