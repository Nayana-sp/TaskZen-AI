from dateparser.search import search_dates

print("Starting search_dates...")
res = search_dates("I have a exam tomorrow.", settings={'PREFER_DATES_FROM': 'future', 'STRICT_PARSING': False})
print("Result:", res)
