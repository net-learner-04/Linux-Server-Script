import re
import config

# auditd hex-encodes EXECVE arguments that contain spaces, quotes, or
# non-printable characters, so the raw log shows unreadable hex strings
# instead of the actual command text.
_HEX_PATTERN = re.compile(r'^[0-9A-Fa-f]+$')

# Only EXECVE argument fields (a0, a1, a2, ...) are ever hex-encoded by
# auditd. Other bare numeric fields (uid, pid, arch, syscall, ...) are
# plain numbers, not hex-encoded text, and must never be run through
# decode_execve_arg() even if they happen to look like valid hex
# (e.g. uid=1000, syscall=59, arch=c000003e).
_EXECVE_ARG_KEY_PATTERN = re.compile(r'^a[0-9]+$')

# Detects an ENRICHED-format translated field (e.g. AUID=, UID=, ARCH=)
# glued directly onto the previous field with no space between them.
# Requires the char right before the match to be neither whitespace nor
# an uppercase letter, so it won't re-match partway through an existing
# uppercase run (e.g. the "Y" inside "SYSCALL=").
_ENRICHED_GLUE_PATTERN = re.compile(r'(?<=[^\sA-Z])([A-Z][A-Z0-9_]*=)')


def is_suspicious(cmd_line: str) -> bool:
    '''Check whether a command line contains any keyword worth reporting.'''
    return bool(config._KEYWORD_PATTERN.search(cmd_line))


def decode_execve_arg(arg: str) -> str:
    '''Decode a single EXECVE argument, converting hex-encoded strings back to plain text.'''
    # auditd only hex-encodes when the value is pure hex chars with an even length;
    # anything else (normal args, already-quoted strings) is left untouched.
    if len(arg) % 2 == 0 and len(arg) > 0 and _HEX_PATTERN.match(arg):
        try:
            return bytes.fromhex(arg).decode("utf-8", errors="replace")
        except ValueError:
            return arg
    return arg


def parse_audit_log(line: str) -> dict:
    '''Parse a raw audit log line into a dictionary of key-value pairs.'''
    # In ENRICHED audit log format, auditd sometimes appends a translated
    # uppercase field (AUID=, UID=, ARCH=, SYSCALL=, etc.) directly after the
    # previous field with no separating space (e.g. key="my_exec_key"ARCH=x86_64).
    # Without fixing this, the regex below would swallow the next field's name
    # into the previous field's value, silently losing data (like uid).
    # Insert a space before any such glued-on uppercase field first.
    line = _ENRICHED_GLUE_PATTERN.sub(r' \1', line)

    p = r'([a-zA-Z0-9_]+)=(?:"([^"]*)"|([^"\s]+))'
    m = re.findall(p, line)

    data = dict()
    
    for item in m:
        key, quoted_val, bare_val = item[0], item[1], item[2]

        # auditd quotes a value only when it's already printable text; a bare
        # (unquoted) token means it was hex-encoded, so only decode that case.
        # This avoids mistakenly "decoding" quoted numeric strings like a
        # chmod mode ("0600") or a port number ("22") that just happen to
        # look like valid hex.
        if quoted_val:
            value = quoted_val
        else:
            # Restrict hex-decoding to EXECVE argument fields only (a0, a1, ...).
            # Plain bare numeric fields like uid=1000 or syscall=59 must stay
            # as-is, since they'd otherwise be wrongly "decoded" into garbage
            # bytes just because they happen to look like valid hex.
            if _EXECVE_ARG_KEY_PATTERN.match(key):
                value = decode_execve_arg(bare_val)
            else:
                value = bare_val

        data[key] = value
    
    return data
