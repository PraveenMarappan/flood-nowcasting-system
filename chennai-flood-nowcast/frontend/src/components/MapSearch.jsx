import React, { useState, useEffect, useRef } from 'react';
import { Search, X, Loader2, MapPin } from 'lucide-react';

function determineZoom(item) {
  if (item.isCoord) return 16;

  const type = (item.type || '').toLowerCase();
  const addresstype = (item.addresstype || '').toLowerCase();
  const cls = (item.class || '').toLowerCase();
  const address = item.address || {};

  // City / Municipality / Administrative boundary -> zoom 13
  if (
    ['city', 'town', 'municipality', 'administrative'].includes(type) ||
    ['city', 'town'].includes(addresstype) ||
    cls === 'boundary'
  ) {
    return 13;
  }

  // Suburb / Neighborhood / Locality / District -> zoom 14
  if (
    ['suburb', 'neighbourhood', 'locality', 'district', 'quarter'].includes(type) ||
    ['suburb', 'neighbourhood'].includes(addresstype)
  ) {
    return 14;
  }

  // Street / Road / Highway -> zoom 16
  if (
    ['residential', 'unclassified', 'tertiary', 'secondary', 'primary', 'trunk', 'footway', 'pedestrian', 'road'].includes(type) ||
    cls === 'highway' ||
    address.road
  ) {
    return 16;
  }

  // Building / House / Point of Interest -> zoom 17
  if (
    ['building', 'house', 'amenity', 'shop', 'tourism', 'landmark', 'attraction', 'place_of_worship'].includes(type) ||
    ['amenity', 'building', 'shop', 'tourism', 'historic', 'leisure'].includes(cls) ||
    address.house_number
  ) {
    return 17;
  }

  return 14;
}

export default function MapSearch({ onSelectLocation }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isOpen, setIsOpen] = useState(false);

  const containerRef = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;

    setError(null);
    setResults([]);
    setIsOpen(false);

    // 1. Coordinate Search Support: "lat, lon"
    const coordMatch = trimmed.match(/^^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (coordMatch) {
      const lat = parseFloat(coordMatch[1]);
      const lon = parseFloat(coordMatch[2]);

      if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        const coordItem = {
          id: `coord-${lat}-${lon}`,
          display_name: `Coordinates: ${lat.toFixed(4)}, ${lon.toFixed(4)}`,
          main_text: `${lat.toFixed(4)}, ${lon.toFixed(4)}`,
          secondary_text: `Geographic Coordinates`,
          lat,
          lon,
          zoom: 16,
          isCoord: true
        };
        onSelectLocation(coordItem);
        setQuery(`${lat.toFixed(4)}, ${lon.toFixed(4)}`);
        return;
      } else {
        setError('Invalid coordinates. Latitude must be -90 to 90 and Longitude -180 to 180.');
        setIsOpen(true);
        return;
      }
    }

    // 2. OpenStreetMap Nominatim Geocoding
    setLoading(true);
    try {
      const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(trimmed)}&format=json&limit=5&addressdetails=1`;
      const res = await fetch(url, {
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }

      const data = await res.json();
      if (!Array.isArray(data) || data.length === 0) {
        setError('No location found. Try a different city, street or address.');
        setIsOpen(true);
      } else {
        const parsedItems = data.map((item, idx) => {
          const lat = parseFloat(item.lat);
          const lon = parseFloat(item.lon);
          const parts = (item.display_name || '').split(',').map((s) => s.trim());
          const main_text = parts[0] || 'Location';
          const secondary_text = parts.slice(1).join(', ') || '';
          const zoom = determineZoom(item);

          return {
            id: item.place_id || `result-${idx}`,
            display_name: item.display_name,
            main_text,
            secondary_text,
            lat,
            lon,
            zoom,
            type: item.type,
            class: item.class,
            address: item.address
          };
        });

        setResults(parsedItems);
        setIsOpen(true);
      }
    } catch (err) {
      console.error('Geocoding search error:', err);
      setError('Unable to search right now. Please try again.');
      setIsOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (item) => {
    setIsOpen(false);
    setError(null);
    onSelectLocation(item);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setError(null);
    setIsOpen(false);
  };

  return (
    <div className="map-search-wrapper" ref={containerRef}>
      <form className="map-search-bar" onSubmit={handleSearch}>
        <Search size={18} className="map-search-icon" />
        <input
          type="text"
          className="map-search-input"
          placeholder="Search city, street or address..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search map location by city, street, address, or coordinates"
        />
        {query && (
          <button
            type="button"
            className="map-search-clear"
            onClick={handleClear}
            aria-label="Clear search input"
          >
            <X size={16} />
          </button>
        )}
        <button
          type="submit"
          className="map-search-btn"
          disabled={loading}
          aria-label="Perform map search"
        >
          {loading ? (
            <span className="map-search-btn-loading">
              <Loader2 size={14} className="animate-spin" /> Searching...
            </span>
          ) : (
            'Search'
          )}
        </button>
      </form>

      {isOpen && (
        <div className="map-search-dropdown">
          {error ? (
            <div className="map-search-error">{error}</div>
          ) : (
            results.map((item) => (
              <div
                key={item.id}
                className="map-search-item"
                onClick={() => handleSelect(item)}
              >
                <MapPin size={16} className="map-search-item-pin" />
                <div className="map-search-item-text">
                  <div className="map-search-item-main">{item.main_text}</div>
                  {item.secondary_text && (
                    <div className="map-search-item-secondary">{item.secondary_text}</div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
