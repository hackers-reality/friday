"""
Friday Compiler/Interpreter - Language processing.
Lexer, parser, AST, and simple language interpreter.
"""
from __future__ import annotations

import re
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ─── Token Types ───────────────────────────#

class TokenType(Enum):
    """Token types for the language."""
    # Literals
    NUMBER = "NUMBER"
    STRING = "STRING"
    IDENTIFIER = "IDENTIFIER"
    BOOLEAN = "BOOLEAN"
    
    # Operators
    PLUS = "PLUS"
    MINUS = "MINUS"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    ASSIGN = "ASSIGN"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"
    LESS = "LESS"
    GREATER = "GREATER"
    
    # Keywords
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    FOR = "FOR"
    DEF = "DEF"
    RETURN = "RETURN"
    PRINT = "PRINT"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    
    # Structure
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    COMMA = "COMMA"
    SEMICOLON = "SEMICOLON"
    
    EOF = "EOF"


# ─── Token ───────────────────────────#

@dataclass
class Token:
    """Represents a token."""
    type: TokenType
    value: Any
    line: int = 0
    
    def __repr__(self):
        return f"Token({self.type}, {self.value})"


# ─── Lexer ───────────────────────────#

class Lexer:
    """Lexical analyzer for FridayLang."""
    
    KEYWORDS = {
        "if": TokenType.IF,
        "else": TokenType.ELSE,
        "while": TokenType.WHILE,
        "for": TokenType.FOR,
        "def": TokenType.DEF,
        "return": TokenType.RETURN,
        "print": TokenType.PRINT,
        "true": TokenType.BOOLEAN,
        "false": TokenType.BOOLEAN,
        "and": TokenType.AND,
        "or": TokenType.OR,
        "not": TokenType.NOT,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        
    def tokenize(self) -> List[Token]:
        """Convert source code to tokens."""
        tokens = []
        
        while self.pos < len(self.source):
            char = self.source[self.pos]
            
            # Skip whitespace
            if char in (" ", "\t"):
                self.pos += 1
                continue
                
            # Newline
            if char == "\n":
                self.line += 1
                self.pos += 1
                continue
                
            # Skip comments
            if char == "#":
                while self.pos < len(self.source) and self.source[self.pos] != "\n":
                    self.pos += 1
                continue
                
            # Numbers
            if char.isdigit():
                tokens.append(self._read_number())
                continue
                
            # Strings
            if char in ("'", '"'):
                tokens.append(self._read_string(char))
                continue
                
            # Identifiers/keywords
            if char.isalpha() or char == "_":
                tokens.append(self._read_identifier())
                continue
                
            # Operators
            if char == "+":
                tokens.append(Token(TokenType.PLUS, "+", self.line))
                self.pos += 1
                continue
            if char == "-":
                tokens.append(Token(TokenType.MINUS, "-", self.line))
                self.pos += 1
                continue
            if char == "*":
                tokens.append(Token(TokenType.MULTIPLY, "*", self.line))
                self.pos += 1
                continue
            if char == "/":
                tokens.append(Token(TokenType.DIVIDE, "/", self.line))
                self.pos += 1
                continue
            if char == "=":
                if self._peek() == "=":
                    tokens.append(Token(TokenType.EQUAL, "==", self.line))
                    self.pos += 2
                else:
                    tokens.append(Token(TokenType.ASSIGN, "=", self.line))
                    self.pos += 1
                continue
            if char == "!":
                if self._peek() == "=":
                    tokens.append(Token(TokenType.NOT_EQUAL, "!=", self.line))
                    self.pos += 2
                continue
            if char == "<":
                tokens.append(Token(TokenType.LESS, "<", self.line))
                self.pos += 1
                continue
            if char == ">":
                tokens.append(Token(TokenType.GREATER, ">", self.line))
                self.pos += 1
                continue
                
            # Structure
            if char == "(":
                tokens.append(Token(TokenType.LPAREN, "(", self.line))
                self.pos += 1
                continue
            if char == ")":
                tokens.append(Token(TokenType.RPAREN, ")", self.line))
                self.pos += 1
                continue
            if char == "{":
                tokens.append(Token(TokenType.LBRACE, "{", self.line))
                self.pos += 1
                continue
            if char == "}":
                tokens.append(Token(TokenType.RBRACE, "}", self.line))
                self.pos += 1
                continue
            if char == ";":
                tokens.append(Token(TokenType.SEMICOLON, ";", self.line))
                self.pos += 1
                continue
            if char == ",":
                tokens.append(Token(TokenType.COMMA, ",", self.line))
                self.pos += 1
                continue
                
            raise SyntaxError(f"Unknown character: {char} at line {self.line}")
        
        tokens.append(Token(TokenType.EOF, None, self.line))
        return tokens
    
    def _read_number(self) -> Token:
        start = self.pos
        is_float = False
        
        while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == "."):
            if self.source[self.pos] == ".":
                if is_float:
                    break
                is_float = True
            self.pos += 1
        
        num_str = self.source[start:self.pos]
        value = float(num_str) if is_float else int(num_str)
        return Token(TokenType.NUMBER, value, self.line)
    
    def _read_string(self, quote: str) -> Token:
        self.pos += 1  # Skip opening quote
        start = self.pos
        
        while self.pos < len(self.source) and self.source[self.pos] != quote:
            self.pos += 1
        
        string_val = self.source[start:self.pos]
        self.pos += 1  # Skip closing quote
        return Token(TokenType.STRING, string_val, self.line)
    
    def _read_identifier(self) -> Token:
        start = self.pos
        
        while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
            self.pos += 1
        
        ident = self.source[start:self.pos]
        token_type = self.KEYWORDS.get(ident, TokenType.IDENTIFIER)
        value = ident == "true" if token_type == TokenType.BOOLEAN else ident == "false" if token_type == TokenType.BOOLEAN else ident
        return Token(token_type, value, self.line)
    
    def _peek(self) -> Optional[str]:
        if self.pos + 1 < len(self.source):
            return self.source[self.pos + 1]
        return None


# ─── AST Nodes ───────────────────────────#

@dataclass
class ASTNode:
    """Base AST node."""
    pass

@dataclass
class NumberNode(ASTNode):
    value: float

@dataclass
class StringNode(ASTNode):
    value: str

@dataclass
class BooleanNode(ASTNode):
    value: bool

@dataclass
class IdentifierNode(ASTNode):
    name: str

@dataclass
class BinOpNode(ASTNode):
    left: ASTNode
    operator: TokenType
    right: ASTNode

@dataclass
class AssignmentNode(ASTNode):
    name: str
    value: ASTNode

@dataclass
class PrintNode(ASTNode):
    expression: ASTNode

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then_block: List[ASTNode]
    else_block: List[ASTNode]

@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: List[ASTNode]

@dataclass
class FunctionDefNode(ASTNode):
    name: str
    params: List[str]
    body: List[ASTNode]

@dataclass
class FunctionCallNode(ASTNode):
    name: str
    args: List[ASTNode]

@dataclass
class ReturnNode(ASTNode):
    value: Optional[ASTNode]


# ─── Parser ───────────────────────────#

class Parser:
    """Parser for FridayLang."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        
    def parse(self) -> List[ASTNode]:
        """Parse tokens into AST."""
        statements = []
        
        while not self._is_at_end():
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
        
        return statements
    
    def _parse_statement(self) -> Optional[ASTNode]:
        token = self._peek_token()
        
        if token.type == TokenType.DEF:
            return self._parse_function_def()
        elif token.type == TokenType.IF:
            return self._parse_if()
        elif token.type == TokenType.WHILE:
            return self._parse_while()
        elif token.type == TokenType.PRINT:
            return self._parse_print()
        elif token.type == TokenType.RETURN:
            return self._parse_return()
        elif token.type == TokenType.IDENTIFIER:
            return self._parse_assignment_or_call()
        else:
            self._advance()
            return None
    
    def _parse_function_def(self) -> FunctionDefNode:
        self._advance()  # Skip 'def'
        name_token = self._advance()
        name = name_token.value
        
        # Skip '('
        self._advance()
        
        # Parse parameters
        params = []
        if self._peek_token().type != TokenType.RPAREN:
            params.append(self._advance().value)
            while self._peek_token().type == TokenType.COMMA:
                self._advance()  # Skip ','
                params.append(self._advance().value)
        
        # Skip ')'
        self._advance()
        
        # Skip '{'
        self._advance()
        
        # Parse body
        body = []
        while self._peek_token().type != TokenType.RBRACE:
            body.append(self._parse_statement())
        
        # Skip '}'
        self._advance()
        
        return FunctionDefNode(name, params, body)
    
    def _parse_if(self) -> IfNode:
        self._advance()  # Skip 'if'
        
        condition = self._parse_expression()
        
        # Skip '{'
        self._advance()
        
        then_block = []
        while self._peek_token().type != TokenType.RBRACE and self._peek_token().type != TokenType.ELSE:
            then_block.append(self._parse_statement())
        
        # Skip '}'
        self._advance()
        
        else_block = []
        if self._peek_token().type == TokenType.ELSE:
            self._advance()  # Skip 'else'
            self._advance()  # Skip '{'
            while self._peek_token().type != TokenType.RBRACE:
                else_block.append(self._parse_statement())
            self._advance()  # Skip '}'
        
        return IfNode(condition, then_block, else_block)
    
    def _parse_while(self) -> WhileNode:
        self._advance()  # Skip 'while'
        
        condition = self._parse_expression()
        
        # Skip '{'
        self._advance()
        
        body = []
        while self._peek_token().type != TokenType.RBRACE:
            body.append(self._parse_statement())
        
        # Skip '}'
        self._advance()
        
        return WhileNode(condition, body)
    
    def _parse_print(self) -> PrintNode:
        self._advance()  # Skip 'print'
        self._advance()  # Skip '('
        
        expr = self._parse_expression()
        
        self._advance()  # Skip ')'
        
        return PrintNode(expr)
    
    def _parse_return(self) -> ReturnNode:
        self._advance()  # Skip 'return'
        value = self._parse_expression()
        return ReturnNode(value)
    
    def _parse_assignment_or_call(self) -> ASTNode:
        name_token = self._advance()
        name = name_token.value
        
        if self._peek_token().type == TokenType.ASSIGN:
            self._advance()  # Skip '='
            value = self._parse_expression()
            return AssignmentNode(name, value)
        elif self._peek_token().type == TokenType.LPAREN:
            self._advance()  # Skip '('
            
            args = []
            if self._peek_token().type != TokenType.RPAREN:
                args.append(self._parse_expression())
                while self._peek_token().type == TokenType.COMMA:
                    self._advance()  # Skip ','
                    args.append(self._parse_expression())
            
            self._advance()  # Skip ')'
            return FunctionCallNode(name, args)
        else:
            return IdentifierNode(name)
    
    def _parse_expression(self) -> ASTNode:
        left = self._parse_term()
        
        while self._peek_token().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance().type
            right = self._parse_term()
            left = BinOpNode(left, op, right)
        
        return left
    
    def _parse_term(self) -> ASTNode:
        left = self._parse_factor()
        
        while self._peek_token().type in (TokenType.MULTIPLY, TokenType.DIVIDE):
            op = self._advance().type
            right = self._parse_factor()
            left = BinOpNode(left, op, right)
        
        return left
    
    def _parse_factor(self) -> ASTNode:
        token = self._peek_token()
        
        if token.type == TokenType.NUMBER:
            self._advance()
            return NumberNode(token.value)
        elif token.type == TokenType.STRING:
            self._advance()
            return StringNode(token.value)
        elif token.type == TokenType.BOOLEAN:
            self._advance()
            return BooleanNode(token.value)
        elif token.type == TokenType.IDENTIFIER:
            # Could be variable or function call
            return self._parse_assignment_or_call()
        elif token.type == TokenType.LPAREN:
            self._advance()  # Skip '('
            expr = self._parse_expression()
            self._advance()  # Skip ')'
            return expr
        else:
            raise SyntaxError(f"Unexpected token: {token}")
    
    def _peek_token(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # EOF
    
    def _advance(self) -> Token:
        token = self._peek_token()
        self.pos += 1
        return token
    
    def _is_at_end(self) -> bool:
        return self._peek_token().type == TokenType.EOF


# ─── Interpreter ───────────────────────────#

class Interpreter:
    """Interpreter for FridayLang."""
    
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, FunctionDefNode] = {}
        self.output: List[str] = []
        
    def interpret(self, ast: List[ASTNode]) -> Any:
        """Execute the AST."""
        result = None
        
        for node in ast:
            result = self._execute(node)
            if isinstance(result, ReturnValue):
                result = result.value
                break
        
        return result
    
    def _execute(self, node: ASTNode) -> Any:
        if isinstance(node, NumberNode):
            return node.value
        
        elif isinstance(node, StringNode):
            return node.value
        
        elif isinstance(node, BooleanNode):
            return node.value
        
        elif isinstance(node, IdentifierNode):
            if node.name not in self.variables:
                raise NameError(f"Undefined variable: {node.name}")
            return self.variables[node.name]
        
        elif isinstance(node, BinOpNode):
            left = self._execute(node.left)
            right = self._execute(node.right)
            
            if node.operator == TokenType.PLUS:
                return left + right
            elif node.operator == TokenType.MINUS:
                return left - right
            elif node.operator == TokenType.MULTIPLY:
                return left * right
            elif node.operator == TokenType.DIVIDE:
                return left / right
            
        elif isinstance(node, AssignmentNode):
            value = self._execute(node.value)
            self.variables[node.name] = value
            return value
        
        elif isinstance(node, PrintNode):
            value = self._execute(node.expression)
            self.output.append(str(value))
            print(value)
            return value
        
        elif isinstance(node, IfNode):
            condition = self._execute(node.condition)
            
            if condition:
                for stmt in node.then_block:
                    result = self._execute(stmt)
                    if isinstance(result, ReturnValue):
                        return result
            else:
                for stmt in node.else_block:
                    result = self._execute(stmt)
                    if isinstance(result, ReturnValue):
                        return result
            
            return None
        
        elif isinstance(node, WhileNode):
            while self._execute(node.condition):
                for stmt in node.body:
                    result = self._execute(stmt)
                    if isinstance(result, ReturnValue):
                        return result
            return None
        
        elif isinstance(node, FunctionDefNode):
            self.functions[node.name] = node
            return None
        
        elif isinstance(node, FunctionCallNode):
            if node.name not in self.functions:
                raise NameError(f"Undefined function: {node.name}")
            
            func = self.functions[node.name]
            
            # Evaluate arguments
            args = [self._execute(arg) for arg in node.args]
            
            # Create new scope
            old_vars = self.variables.copy()
            
            # Set parameters
            for param, value in zip(func.params, args):
                self.variables[param] = value
            
            # Execute function body
            result = None
            for stmt in func.body:
                result = self._execute(stmt)
                if isinstance(result, ReturnValue):
                    result = result.value
                    break
            
            # Restore scope
            self.variables = old_vars
            
            return result
        
        elif isinstance(node, ReturnNode):
            value = self._execute(node.value)
            return ReturnValue(value)
        
        return None


class ReturnValue:
    """Wrapper to handle return values."""
    def __init__(self, value: Any):
        self.value = value


# ─── Language Tool ───────────────────────────#

def compile_tool(
    action: str = "tokenize",
    code: str = None,
) -> str:
    """
    Friday tool for language processing.
    Actions: tokenize, parse, interpret, run
    """
    if not code:
        return "[FAIL] Code required."
    
    if action == "tokenize":
        try:
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            lines = ["### TOKENS", ""]
            for t in tokens[:50]:
                lines.append(f"{t.type}: {t.value}")
            return "\n".join(lines)
        except SyntaxError as e:
            return f"[FAIL] Lexer error: {e}"
    
    if action == "parse":
        try:
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
            lines = ["### AST", ""]
            for node in ast:
                lines.append(f"{node}")
            return "\n".join(lines)
        except SyntaxError as e:
            return f"[FAIL] Parser error: {e}"
    
    if action == "interpret" or action == "run":
        try:
            lexer = Lexer(code)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
            interpreter = Interpreter()
            result = interpreter.interpret(ast)
            lines = ["### INTERPRETER OUTPUT", ""]
            lines.extend(interpreter.output)
            if result is not None:
                lines.append(f"Result: {result}")
            return "\n".join(lines)
        except Exception as e:
            return f"[FAIL] Runtime error: {e}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Compiler/Interpreter...\n")
    
    # Test code
    test_code = """
    # Simple FridayLang program
    x = 10
    y = 20
    print(x + y)
    
    def add(a, b) {
        return a + b
    }
    
    print(add(5, 3))
    """
    
    print("--- Tokenize ---")
    print(compile_tool("tokenize", code=test_code))
    
    print("\n--- Run ---")
    print(compile_tool("run", code=test_code))
