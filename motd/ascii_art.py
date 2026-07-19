import random


ASCII = r"""
 .oooooo..o                                                   
d8P'    `Y8                                                   
Y88bo.       .ooooo.  oooo d8b oooo    ooo  .ooooo.  oooo d8b 
 `"Y8888o.  d88' `88b `888""8P  `88.  .8'  d88' `88b `888""8P 
     `"Y88b 888ooo888  888       `88..8'   888ooo888  888     
oo     .d8P 888    .o  888        `888'    888    .o  888     
8""88888P'  `Y8bod8P' d888b        `8'     `Y8bod8P' d888b    
"""


# Color list
COLORS = [
    "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF",
    "#D7BAFF", "#E0BBE4", "#FEC8D8", "#FFDAC1", "#B5EAD7",
    "#C7CEEA", "#CDE7BE", "#F6DFEB", "#FBE7C6", "#A0E7E5",
    "#B4F8C8", "#D4F0F0", "#F9F7CF", "#E2F0CB", "#D0F4DE",
    "#F8C8DC", "#C9E4DE", "#D6EADF", "#E4C1F9", "#A9DEF9",
    "#FCF6BD", "#FFD6A5", "#FDFFB6", "#CAFFBF", "#9BF6FF"
]


def get_art():
    return ASCII


def get_color():
    return random.choice(COLORS)
