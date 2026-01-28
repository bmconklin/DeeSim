#!/usr/bin/env python3
import sys
import requests
import json
import logging
from typing import List, Dict, Any, Optional
from src.dnd.core.cache import APICache
from datetime import datetime

logger = logging.getLogger(__name__)

# Base URL for the D&D 5e API
BASE_URL = "https://www.dnd5eapi.co/api"

# Request timeout in seconds
REQUEST_TIMEOUT = 10

# Category descriptions for better resource discovery
CATEGORY_DESCRIPTIONS = {
    "ability-scores": "The six abilities that describe a character's physical and mental characteristics",
    "alignments": "The moral and ethical attitudes and behaviors of creatures",
    "backgrounds": "Character backgrounds and their features",
    "classes": "Character classes with features, proficiencies, and subclasses",
    "conditions": "Status conditions that affect creatures",
    "damage-types": "Types of damage that can be dealt",
    "equipment": "Items, weapons, armor, and gear for adventuring",
    "equipment-categories": "Categories of equipment",
    "feats": "Special abilities and features",
    "features": "Class and racial features",
    "languages": "Languages spoken throughout the multiverse",
    "magic-items": "Magical equipment with special properties",
    "magic-schools": "Schools of magic specialization",
    "monsters": "Creatures and foes",
    "proficiencies": "Skills and tools characters can be proficient with",
    "races": "Character races and their traits",
    "rule-sections": "Sections of the game rules",
    "rules": "Game rules",
    "skills": "Character skills tied to ability scores",
    "spells": "Magic spells with effects, components, and descriptions",
    "subclasses": "Specializations within character classes",
    "subraces": "Variants of character races",
    "traits": "Racial traits",
    "weapon-properties": "Special properties of weapons"
}

def prefetch_category_items(category: str, cache: APICache) -> None:
    """Prefetch and cache all items in a category.

    Args:
        category: The D&D API category to prefetch
        cache: The API cache to use
    """
    logger.info(f"Prefetching items for category: {category}")

    # First get the list of items
    cache_key = f"dnd_items_{category}"
    category_data = cache.get(cache_key)

    if not category_data:
        try:
            logger.debug(f"Fetching item list for category: {category}")
            response = requests.get(
                f"{BASE_URL}/{category}", timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                logger.error(
                    f"Failed to fetch items for {category}: {response.status_code}")
                return

            data = response.json()

            # Transform to resource format
            items = []
            for item in data.get("results", []):
                items.append({
                    "name": item["name"],
                    "index": item["index"],
                    "description": f"Details about {item['name']}",
                    "uri": f"resource://dnd/item/{category}/{item['index']}"
                })

            category_data = {
                "category": category,
                "items": items,
                "count": len(items)
            }

            # Cache the result
            cache.set(cache_key, category_data)

        except Exception as e:
            logger.exception(
                f"Error prefetching items for {category}: {e}")
            return

    # Now prefetch each individual item
    for item in category_data["items"]:
        item_cache_key = f"dnd_item_{category}_{item['index']}"
        if not cache.get(item_cache_key):
            try:
                logger.debug(
                    f"Prefetching item details: {category}/{item['index']}")
                response = requests.get(
                    f"{BASE_URL}/{category}/{item['index']}", timeout=REQUEST_TIMEOUT)
                if response.status_code == 200:
                    data = response.json()
                    cache.set(item_cache_key, data)
            except Exception as e:
                logger.exception(
                    f"Error prefetching item {category}/{item['index']}: {e}")

def get_categories(cache: Optional[APICache] = None) -> Dict[str, Any]:
    """List all available D&D 5e API categories for browsing the official content."""
    logger.debug("Fetching D&D API categories")

    # Check cache first
    if cache:
        cached_data = cache.get("dnd_categories")
        if cached_data:
            return cached_data

    # Fetch from API if not in cache
    try:
        response = requests.get(f"{BASE_URL}/", timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            logger.error(
                f"Failed to fetch categories: {response.status_code}")
            return {"error": f"API request failed with status {response.status_code}"}

        data = response.json()

        # Transform to resource format with descriptions
        categories = []
        for key in data.keys():
            description = CATEGORY_DESCRIPTIONS.get(
                key, f"Collection of D&D 5e {key}")
            categories.append({
                "name": key,
                "description": description,
                "uri": f"resource://dnd/items/{key}"
            })

        result = {
            "categories": categories,
            "count": len(categories)
        }

        # Cache the result
        if cache:
            cache.set("dnd_categories", result)
        return result

    except Exception as e:
        logger.exception(f"Error fetching categories: {e}")
        return {"error": f"Failed to fetch categories: {str(e)}"}

def get_items(category: str, cache: Optional[APICache] = None) -> Dict[str, Any]:
    """Retrieve a list of all items available in a specific D&D 5e API category."""
    logger.debug(f"Fetching items for category: {category}")

    # Check cache first
    cache_key = f"dnd_items_{category}"
    if cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

    # Fetch from API if not in cache
    try:
        response = requests.get(
            f"{BASE_URL}/{category}", timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            logger.error(
                f"Failed to fetch items for {category}: {response.status_code}")
            return {"error": f"Category '{category}' not found or API request failed"}

        data = response.json()

        # Transform to resource format
        items = []
        for item in data.get("results", []):
            item_uri = f"resource://dnd/item/{category}/{item['index']}"
            items.append({
                "name": item["name"],
                "index": item["index"],
                "uri": item_uri,
            })

        result = {
            "category": category,
            "count": len(items),
            "items": items,
            "source": "D&D 5e API (www.dnd5eapi.co)",
        }

        # Cache the result
        if cache:
            cache.set(cache_key, result)
        return result

    except Exception as e:
        logger.exception(f"Error fetching items for {category}: {e}")
        return {"error": f"Failed to fetch items for {category}: {str(e)}"}

def get_item(category: str, index: str, cache: Optional[APICache] = None) -> Dict[str, Any]:
    """Retrieve detailed information about a specific D&D 5e item by its category and index."""
    logger.debug(f"Fetching item details: {category}/{index}")

    # Check cache first
    cache_key = f"dnd_item_{category}_{index}"
    if cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

    # Fetch from API if not in cache
    try:
        response = requests.get(
            f"{BASE_URL}/{category}/{index}", timeout=REQUEST_TIMEOUT)

        # Handle redirects (common in the D&D API)
        if response.status_code == 301 and 'Location' in response.headers:
            redirect_url = response.headers['Location']
            logger.debug(f"Following redirect to: {redirect_url}")
            response = requests.get(redirect_url, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            logger.error(
                f"Failed to fetch item {category}/{index}: {response.status_code}")
            return {"error": f"Item '{index}' not found in category '{category}' or API request failed"}

        # Add source attribution to the API response
        data = response.json()
        data["source"] = "D&D 5e API (www.dnd5eapi.co)"

        # Cache the result
        if cache:
            cache.set(cache_key, data)
        return data

    except Exception as e:
        logger.exception(f"Error fetching item {category}/{index}: {e}")
        return {"error": f"Failed to fetch item {category}/{index}: {str(e)}"}

def search_category(category: str, query: str, cache: Optional[APICache] = None) -> Dict[str, Any]:
    """Search for D&D 5e items within a specific category that match the provided query."""
    logger.debug(f"Searching in {category} for: {query}")

    # Get all items in the category
    all_items = get_items(category, cache=cache)

    # Handle error cases
    if "error" in all_items:
        return all_items

    # Filter items by search term
    matching_items = []
    for item in all_items.get("items", []):
        if query.lower() in item["name"].lower():
            matching_items.append(item)

    result = {
        "category": category,
        "query": query,
        "count": len(matching_items),
        "items": matching_items,
        "source": "D&D 5e API (www.dnd5eapi.co)",
    }

    return result

def check_api_status() -> Dict[str, Any]:
    """Check the current status and health of the D&D 5e API connection."""
    logger.debug("Checking D&D 5e API status")

    try:
        start_time = datetime.now()
        response = requests.get(BASE_URL, timeout=REQUEST_TIMEOUT)
        response_time = (datetime.now() - start_time).total_seconds()

        if response.status_code == 200:
            data = response.json()
            available_endpoints = list(data.keys())

            return {
                "status": "online",
                "response_time_seconds": response_time,
                "available_endpoints": available_endpoints,
                "base_url": BASE_URL,
                "source": "D&D 5e API Status Check"
            }
        else:
            return {
                "status": "error",
                "response_code": response.status_code,
                "response_time_seconds": response_time,
                "message": f"API returned non-200 status code: {response.status_code}",
                "source": "D&D 5e API Status Check"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to D&D 5e API: {str(e)}",
            "source": "D&D 5e API Status Check"
        }

def register_resources(app, cache: APICache):
    """Register D&D API resources with the FastMCP app."""
    print("Registering D&D API resources...", file=sys.stderr)

    # Start prefetching common categories in the background
    import threading
    for category in ["spells", "equipment", "monsters", "classes", "races"]:
        threading.Thread(target=prefetch_category_items,
                         args=(category, cache), daemon=True).start()

    @app.resource("resource://dnd/categories")
    def _get_categories() -> Dict[str, Any]:
        return get_categories(cache=cache)

    @app.resource("resource://dnd/items/{category}")
    def _get_items(category: str) -> Dict[str, Any]:
        return get_items(category, cache=cache)

    @app.resource("resource://dnd/item/{category}/{index}")
    def _get_item(category: str, index: str) -> Dict[str, Any]:
        return get_item(category, index, cache=cache)

    @app.resource("resource://dnd/search/{category}/{query}")
    def _search_category(category: str, query: str) -> Dict[str, Any]:
        return search_category(category, query, cache=cache)

    @app.resource("resource://dnd/api_status")
    def _check_api_status() -> Dict[str, Any]:
        return check_api_status()

    print("D&D API resources registered successfully", file=sys.stderr)
