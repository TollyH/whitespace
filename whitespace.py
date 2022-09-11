SPACE = ' '
TAB = '\t'
LINE_FEED = '\n'
WHITESPACE = {SPACE, TAB, LINE_FEED}


def _ws_remove_comments(code: str) -> str:
    return ''.join([x for x in code if x in WHITESPACE])


def _ws_number(code: str) -> int:
    code_pos = 0
    if code[code_pos] == LINE_FEED:
        raise RuntimeError(
            "Expected a sign symbol before terminal when parsing number at "
            + f"position {code_pos}"
        )
    negative = code[code_pos] == TAB
    code_pos += 1
    binary_rep = '-0' if negative else '0'
    while code[code_pos] != LINE_FEED:
        if code[code_pos] == SPACE:
            binary_rep += '0'
        elif code[code_pos] == TAB:
            binary_rep += '1'
        code_pos += 1
    return int(binary_rep, 2)


def _ws_label(code: str) -> str:
    code_pos = 0
    label = ''
    while code[code_pos] != LINE_FEED:
        label += code[code_pos]
        code_pos += 1
    return label


def _ws_input_number(inp: str, input_pos: int) -> tuple[int, int]:
    if inp[input_pos] == '0':
        if inp[input_pos + 1].lower() == 'x':
            base = 16  # Hex
            input_pos += 2
        elif inp[input_pos + 1].lower() == 'b':
            base = 2  # Bin
            input_pos += 2
        else:
            base = 8  # Oct
            input_pos += 1
    else:
        base = 10  # Dec
    str_repr = ''
    while inp[input_pos] != LINE_FEED:
        str_repr += inp[input_pos]
        input_pos += 1
    input_pos += 1
    return int(str_repr, base), input_pos


def _ws_tokenize_stack(code: str) -> str:
    token = SPACE
    code_pos = 0
    space_or_tab = False
    if code[1] == SPACE:
        token += SPACE
        space_or_tab = True
        code_pos = 2
    elif code[1] == TAB:
        token += TAB + code[2]
        space_or_tab = True
        code_pos = 3
    elif code[1] == LINE_FEED:
        token += LINE_FEED + code[2]
    if space_or_tab:
        while code[code_pos] != LINE_FEED:
            token += code[code_pos]
            code_pos += 1
        token += LINE_FEED
    return token


def _ws_tokenize_arithmetic(code: str) -> str:
    return TAB + SPACE + code[2] + code[3]


def _ws_tokenize_heap(code: str) -> str:
    return TAB + TAB + code[2]


def _ws_tokenize_io(code: str) -> str:
    return TAB + LINE_FEED + code[2] + code[3]


def _ws_tokenize_flow_control(code: str) -> tuple[str, None | str]:
    token = LINE_FEED + code[1] + code[2]
    label: None | str = None
    if code[1] == SPACE or (code[1] == TAB and code[2] != LINE_FEED):
        label_param = _ws_label(code[3:])
        token += label_param + LINE_FEED
        if code[1] == SPACE and code[2] == SPACE:
            label = label_param
    return token, label


def _ws_tokenize(code: str, labels: dict[str, int]) -> list[str]:
    code_tokens: list[str] = []
    code_pos = 0
    while code_pos < len(code):
        if code[code_pos] == SPACE:
            new_token = _ws_tokenize_stack(code[code_pos:])
            code_tokens.append(new_token)
            code_pos += len(new_token)
        elif code[code_pos] == TAB:
            if code[code_pos + 1] == SPACE:
                new_token = _ws_tokenize_arithmetic(code[code_pos:])
                code_tokens.append(new_token)
                code_pos += len(new_token)
            elif code[code_pos + 1] == TAB:
                new_token = _ws_tokenize_heap(code[code_pos:])
                code_tokens.append(new_token)
                code_pos += len(new_token)
            elif code[code_pos + 1] == LINE_FEED:
                new_token = _ws_tokenize_io(code[code_pos:])
                code_tokens.append(new_token)
                code_pos += len(new_token)
        elif code[code_pos] == LINE_FEED:
            new_token, label = _ws_tokenize_flow_control(code[code_pos:])
            if label is not None:
                if label in labels:
                    raise SyntaxError(
                        f"Label with name {label} defined multiple times")
                labels[label] = len(code_tokens)
            code_tokens.append(new_token)
            code_pos += len(new_token)
    return code_tokens


def _ws_code_stack(code: str, stack: list[int]) -> None:
    if code[1] == SPACE:
        # Push number to stack.
        stack.append(_ws_number(code[2:]))
    elif code[1] == TAB:
        if code[2] == SPACE:
            # Duplicate item at a specified position in the stack to the top.
            parsed_int = _ws_number(code[3:])
            if parsed_int < 0:
                raise RuntimeError(f"Stack index of {parsed_int} is below 0")
            stack.append(stack[-(parsed_int + 1)])
        elif code[2] == LINE_FEED:
            # Remove a specified number of items from the top of the stack,
            # but leaving the top-most value in place.
            parsed_int = _ws_number(code[3:])
            if parsed_int < 0 or parsed_int >= len(stack):
                parsed_int = len(stack) - 1
            for _ in range(parsed_int):
                if len(stack) <= 1:
                    break
                stack.pop(-2)
        else:
            raise RuntimeError(
                "TAB + TAB is not a valid instruction for the Stack IMP")
    elif code[1] == LINE_FEED:
        if code[2] == SPACE:
            # Duplicate the top item of the stack.
            stack.append(stack[-1])
        elif code[2] == TAB:
            # Swap the top two items in the stack.
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif code[2] == LINE_FEED:
            # Remove the top-most item from the stack.
            stack.pop(-1)


def _ws_code_arithmetic(code: str, stack: list[int]) -> None:
    if code[2] == SPACE:
        if code[3] == SPACE:
            # Take the top two values off the stack, then push their sum to the
            # top of the stack.
            stack.append(stack.pop(-2) + stack.pop(-1))
        elif code[3] == TAB:
            # Take the top two values off the stack, then push their
            # difference to the top of the stack.
            stack.append(stack.pop(-2) - stack.pop(-1))
        elif code[3] == LINE_FEED:
            # Take the top two values off the stack, then push their product
            # to the top of the stack.
            stack.append(stack.pop(-2) * stack.pop(-1))
    elif code[2] == TAB:
        if code[3] == SPACE:
            # Take the top two values off the stack, then push their floored
            # quotient to the top of the stack.
            stack.append(stack.pop(-2) // stack.pop(-1))
        elif code[3] == TAB:
            # Take the top two values off the stack, then push the remainder
            # of their division to the top of the stack.
            stack.append(stack.pop(-2) % stack.pop(-1))
        else:
            raise RuntimeError(
                "TAB + LINE FEED is not a valid instruction for the Arithmetic"
                + " IMP")
    else:
        raise RuntimeError(
            "LINE FEED is not a valid instruction for the Arithmetic IMP")


def _ws_code_heap(code: str, stack: list[int], heap: dict[int, int]) -> None:
    if code[2] == SPACE:
        # Take the top two values off the stack, then store the second at
        # the address with the value of the first.
        # In Python assignment the RIGHT side is evaluated first.
        heap[stack.pop(-1)] = stack.pop(-1)
    elif code[2] == TAB:
        # Take the top-most value off the stack, then store the value in the
        # heap with that address on the top of the stack.
        stack.append(heap[stack.pop(-1)])
    else:
        raise RuntimeError(
            "LINE FEED is not a valid instruction for the Heap IMP")


def _ws_code_io(code: str, stack: list[int], heap: dict[int, int],
                output: list[str], inp: str, input_pos: int) -> int:
    if code[2] == SPACE:
        if code[3] == SPACE:
            # Take the top-most value off the stack and add its ASCII character
            # to the output.
            output.append(chr(stack.pop(-1)))
        elif code[3] == TAB:
            # Take the top-most value off the stack and add its string
            # representation to the output.
            output.append(str(stack.pop(-1)))
        else:
            raise RuntimeError(
                "SPACE + LINE FEED is not a valid instruction for the "
                + "Input/Output IMP")
    elif code[2] == TAB:
        try:
            if code[3] == SPACE:
                # Remove the top-most value in the stack, then store the ASCII
                # value of the next character in input at that address in the
                # heap.
                heap[stack.pop(-1)] = ord(inp[input_pos])
                input_pos += 1
            elif code[3] == TAB:
                # Remove the top-most value in the stack, then store the next
                # number in input at that address in the heap.
                parsed_int, input_pos = _ws_input_number(inp, input_pos)
                heap[stack.pop(-1)] = parsed_int
            else:
                raise RuntimeError(
                    "TAB + LINE FEED is not a valid instruction for the "
                    + "Input/Output IMP")
        except IndexError as exc:
            raise RuntimeError(
                "Tried to read past end of input stream. Did "
                + "you provide enough input and terminate numbers with \\n?"
            ) from exc
    else:
        raise RuntimeError(
            "LINE FEED is not a valid instruction for the Input/Output IMP")
    return input_pos


def _ws_code_flow_control(code: str, stack: list[int], labels: dict[str, int],
                          call_stack: list[int], token_pos: int) -> None | int:
    if code[1] == SPACE:
        if code[2] == TAB:
            # Call a subroutine at the specified label by jumping there
            # unconditionally, storing the current position at the top of the
            # call stack.
            parsed_label = _ws_label(code[3:])
            call_stack.append(token_pos + 1)
            return labels[parsed_label]
        elif code[2] == LINE_FEED:
            # Jump unconditionally to the specified label.
            parsed_label = _ws_label(code[3:])
            return labels[parsed_label]
    elif code[1] == TAB:
        if code[2] == SPACE:
            # Remove the top-most value from the stack, then jump to the
            # specified label if the value is zero.
            parsed_label = _ws_label(code[3:])
            if stack.pop(-1) == 0:
                return labels[parsed_label]
        elif code[2] == TAB:
            # Remove the top-most value from the stack, then jump to the
            # specified label if the value is less than zero.
            parsed_label = _ws_label(code[3:])
            if stack.pop(-1) < 0:
                return labels[parsed_label]
        elif code[2] == LINE_FEED:
            # Exit the current subroutine by removing the top-most value from
            # the call stack and jumping unconditionally back to that position.
            return call_stack.pop(-1)
    else:
        raise RuntimeError(
            "LINE FEED is not a valid instruction for the Flow Control IMP")
    return None


def whitespace(code: str, inp: str = '') -> str:
    code = _ws_remove_comments(code)
    output: list[str] = []
    stack: list[int] = []
    heap: dict[int, int] = {}
    labels: dict[str, int] = {}
    call_stack: list[int] = []

    code_tokens = _ws_tokenize(code, labels)
    token_pos = 0
    input_pos = 0
    while token_pos < len(code_tokens):
        token = code_tokens[token_pos]
        if token[0] == SPACE:
            _ws_code_stack(token, stack)
        elif token[0] == TAB:
            if token[1] == SPACE:
                _ws_code_arithmetic(token, stack)
            elif token[1] == TAB:
                _ws_code_heap(token, stack, heap)
            elif token[1] == LINE_FEED:
                input_pos = _ws_code_io(
                    token, stack, heap, output, inp, input_pos)
        elif token[0] == LINE_FEED:
            if token[1] == LINE_FEED and token[2] == LINE_FEED:
                return ''.join(output)
            if token[1] == SPACE and token[2] == SPACE:
                # Token is a label — no action needs to be taken.
                pass
            else:
                new_token_pos = _ws_code_flow_control(
                    token, stack, labels, call_stack, token_pos)
                if new_token_pos is not None:
                    token_pos = new_token_pos - 1
        token_pos += 1
    raise RuntimeError(
        f"Reached end of code unexpectedly. Output was: {output}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        print("You must provide a file path to open")
        sys.exit(-1)
    print("Enter all program input if applicable, using \\n for newlines")
    program_input = input(">>> ").replace('\\n', '\n')
    with open(sys.argv[1], encoding='utf8') as file:
        print(whitespace(file.read(), program_input))
