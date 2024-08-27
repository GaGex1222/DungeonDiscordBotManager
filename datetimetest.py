import datetime

today = datetime.time(0, 0)
incremented_hour = 0
all_hours = []

for _ in range(24):
    all_hours.append(datetime.time(incremented_hour, 0))
    incremented_hour += 1

print([time.strftime("%H:%M") for time in all_hours])

    
    