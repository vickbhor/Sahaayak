import math
import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SahaayakAI-Triage/1.0 (student healthcare project)"


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def parse_elements(elements, lat, lon):
    results = []
    seen = set()
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        if "lat" in el and "lon" in el:
            elat, elon = el["lat"], el["lon"]
        elif "center" in el:
            elat, elon = el["center"]["lat"], el["center"]["lon"]
        else:
            continue

        key = (name, round(elat, 4), round(elon, 4))
        if key in seen:
            continue
        seen.add(key)

        phone = tags.get("phone") or tags.get("contact:phone") or tags.get("contact:mobile")
        address_parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:suburb"),
            tags.get("addr:city") or tags.get("addr:town"),
            tags.get("addr:postcode"),
        ]
        address = ", ".join([p for p in address_parts if p])
        amenity = tags.get("amenity") or tags.get("healthcare") or "hospital"
        distance = round(haversine_km(lat, lon, elat, elon), 2)

        results.append(
            {
                "name": name,
                "type": amenity,
                "phone": phone,
                "address": address or None,
                "emergency": tags.get("emergency") == "yes",
                "latitude": elat,
                "longitude": elon,
                "distance_km": distance,
            }
        )

    results.sort(key=lambda x: x["distance_km"])
    return results


async def fetch_nearby_hospitals(lat, lon, radius_m=10000, limit=20):
    query = f"""
    [out:json][timeout:20];
    (
      node["amenity"="hospital"](around:{radius_m},{lat},{lon});
      way["amenity"="hospital"](around:{radius_m},{lat},{lon});
      node["amenity"="clinic"](around:{radius_m},{lat},{lon});
      way["amenity"="clinic"](around:{radius_m},{lat},{lon});
      node["healthcare"="hospital"](around:{radius_m},{lat},{lon});
    );
    out center tags;
    """
    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.post(
            OVERPASS_URL, data={"data": query}, headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
        data = response.json()

    results = parse_elements(data.get("elements", []), lat, lon)
    return results[:limit]


async def geocode_location(query):
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "in"},
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        data = response.json()

    if not data:
        return None

    return {
        "latitude": float(data[0]["lat"]),
        "longitude": float(data[0]["lon"]),
        "display_name": data[0].get("display_name"),
    }
