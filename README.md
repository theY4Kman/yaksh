yaksh
=====

My attempt at writing a programming language stack. The language itself is based off Python, but as it's a learning project, I include only the features I want to learn to implement.

Sections:
  - [Lexer](#lexer)
  - [Parser](#parser)
  - [Interpreter](#interpreter) (unused)
  - [Bytecode Assembly Generator](#bytecode-assembly-generator)
  - [Bytecode Assembler](#bytecode-assembler)
  - [Virtual Machine](#virtual-machine)


Lexer
=====

The lexer reads in source code and emits Tokens. Tokens logically delimit the source, taking into account literals and identifiers. The Token class includes line and character numbers, though this information isn't yet used for debugging information (the info is lost after parsing).


Parser
======

The parser reads in tokens from the [lexer](#lexer) and emits Symbols. Each Symbol is a container of Tokens and other Symbols.

The Symbol class has been retroactively fitted with some metaclass magic to provide semantic meaning to its contained elements. For instance, CmpStmt accepts 3 children (ValueStmt, CmpOp, ValueStmt), setting the instance variables left, op, and right, respectively. This was done to reduce implementation detail in the [bytecode assembly generator](#bytecode-assembly-generator). The [interpreter](#interp) still uses the old Symbol class, doing the same job but foregoing semantic labels.


Interpreter
===========

The interpreter directly processes and executes the Symbol tree produced by the [parser](#parser). It's not very exciting at all. When I finished the parser, I wanted to run programs, so writing an interpreter fit. Like the rest of the stack, many implementation details, such as how to compare a float to an int, are hidden behind Python.


Bytecode Assembly Generator
===========================

The bytecode assembly generator reads in the Symbol tree produced by the [parser](#parser) and emits yaksh bytecode assembly. The assembly language is very simple, as the [VM](#virtual-machine) is stack-based. To the stack it can load globals and locals using var indices, and inline constants (to be collected by the [assembler](#bytecode-assembler). This may not be the best method, but I haven't run into problems, yet.)

Each instruction has 0 or 1 parameters. Aside from the `LOAD_CONST` instruction, which accepts arbitrary values (at the moment: ints, floats, and strings), parameters are strictly ints.

`LOAD` instructions push to the stack, `STORE` instructions pop from the stack.

Function definitions are mapped to indices, incremented linearly (the first function definition is index 0, the second 1, and so forth), and called with `CALL <idx>`. An explicit set of builtins (see `yaksh.bytecode_asm.BUILTINS`) can be called with `CALL_BUILTIN <idx>`. All arguments should be explicitly pushed to the stack before calling, the first argument pushed first, as all function parameters are popped from the stack with explicit `STORE_VAR` instructions.


Bytecode Assembler
==================

The bytecode assembler reads in bytecode assembly produced by the [assembly generator](#bytecode-assembly-generator) and outputs a compiled yaksh binary to be executed by the [VM](#virtual-machine).

Constants are collected into a table with their values packed (see `yaksh.bytecode_compiler.Const.pack`), and emitted at the beginning of the binary, prefixed by the table size (the size is written specifically to prevent unintentionally reading bytecode when the table is empty).

Function definitions are collected (each starting with a `PROC` and ending with a `MAKE_FUNCTION`) and emitted after the constants table. The function definitions section ends with a final `MAKE_FUNCTION` preceded by a final `PROC`.

The rest of the file is the toplevel instructions.


Virtual Machine
===============

The virtual machine process and executes compiled yaksh binaries (as produced by the [assembler](#bytecode-assembler)). It's stack-based. It's nice and simple.
