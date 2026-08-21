import yaml

with open("data/places.yaml", encoding="utf-8") as f:
    places_data = yaml.safe_load(f)

index = _build_places_index(places_data)

# sanity check: how many total alias entries?
print(len(index))
print(index.get(_normalize("Kalika")))      # should print (level, "kalika")
# same result — suffix present but exact match still works since it's a literal alias
print(index.get(_normalize("Kalika Gaunpalika")))
# should print "kalika" — suffix stripped even though "Kalika Nagarpalika" isn't a real alias
print(_strip_suffix(_normalize("Kalika Nagarpalika")))
