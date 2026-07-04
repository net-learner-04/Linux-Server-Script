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


def get_weather_art(owm_main):
    category = OWM_TO_CATEGORY.get(owm_main, "cloudy")
    return weather_art.get(category, weather_art["cloudy"])
