import pandas as pd

# Load the CSV file with encoding fallback
csv_path = "Movie_Database.csv"  # replace with your actual path
df = pd.read_csv(csv_path, encoding='latin1')

# Extract and process genres
genre_series = df['Genres'].dropna().apply(lambda x: [g.strip() for g in x.split(',')])
unique_genres = sorted(set([genre for sublist in genre_series for genre in sublist]))

print(unique_genres)
