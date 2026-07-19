import re

# sec
INTERVAL = 10

# Discord's hard limit is 2000 chars per message; keep some margin.
DISCORD_LIMIT = 1900

# Keywords used to filter EXECVE command lines that are actually worth reporting.
# Matched against the binary/interpreter name (no options) so variants like
# python3, python3.11, /usr/bin/python are all caught by "python".
# Short tokens (nc, su, sh, dd, etc.) are matched with word boundaries in
# is_suspicious() to avoid false positives like "sync", "bash", "disk".
KEYWORDS = [
    "wget", "curl",        
    "nc", "ncat", "netcat",           
    "chmod",                       
    "base64",                     
    "/etc/shadow", "/etc/sudoers",     
    "rm",                             
    "sudo", "su",                      
    "python", "python3", "perl", "ruby",
    "bash", "sh", "zsh", "dash",     
    "history",                   
    "iptables", "nft",            
    "crontab",    
    "ssh-keygen", "authorized_keys",
    "dd",
    "nohup", "disown",
]

# Pre-compile a single regex with word boundaries for accurate matching.
_KEYWORD_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in KEYWORDS) + r")\b",
    re.IGNORECASE
)
