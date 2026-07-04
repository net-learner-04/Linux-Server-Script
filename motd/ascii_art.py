weather_art = {
    "clear": r"""
        .
      \ | /
    '-.;;;.-'
   -==;;;;;==-
    .-';;;'-.
      / | \
        '
""",
    "cloudy": r"""
   __   _
 _(  )_( )_
(_   _    _)
  (_) (__)
""",
    "rain": r"""
      __   _
    _(  )_( )_
   (_   _    _)
  / /(_) (__)
 / / / / / /
/ / / / / /
""",
    "snow": r"""
.      .
    _\/  \/_
     _\/\/_
 _\_\_\/\/_/_/_
  / /_/\/\_\ \
     _/\/\_
     /\  /\
    '      '
""",
    "thunderstorm": r"""
( (    _-_-_-_- -
 ( (   )- - -
  ( ( ) )
 (_(___)_)
    _<
   / /\
_____\ _________
""",
    "tornado": r"""
--_-_-_-_---
   -_-_-_
    -_-_-
     -__-
    _-_
   _-
   -_
    _-_
"""
}


OWM_TO_CATEGORY = {
    "Clear": "clear",
    "Clouds": "cloudy",
    "Mist": "cloudy",
    "Smoke": "cloudy",
    "Haze": "cloudy",
    "Fog": "cloudy",
    "Dust": "cloudy",
    "Sand": "cloudy",
    "Ash": "cloudy",
    "Squall": "cloudy",
    "Rain": "rain",
    "Drizzle": "rain",
    "Snow": "snow",
    "Thunderstorm": "thunderstorm",
    "Tornado": "tornado",
}


COLORS = {
    "clear": "khaki1",
    "cloudy": "steel_blue1",
    "rain": "sky_blue1",
    "snow": "bright_cyan",
    "thunderstorm": "medium_purple",
    "tornado": "slate_blue1",
}


def get_weather_art(owm_main):
    '''Maps an OWM weather value to a category and 
    returns the corresponding ASCII art string.'''
    category = OWM_TO_CATEGORY.get(owm_main, "cloudy")
    return weather_art.get(category, weather_art["cloudy"])


def get_weather_color(owm_main):
    '''Maps an OWM weather value to a category 
    and returns the corresponding color name.'''
    category = OWM_TO_CATEGORY.get(owm_main, "cloudy")
    return COLORS.get(category, "cyan")
