class Prometheus:
  PROMETHEUS_SERVER = 8000

class Metrics:
  FISH_SPAWNED = {
    "name": "fish_spawned_total",
    "description": "Total number of fish spawned"
  }
  FISH_REMOVED = {
        "name": "fish_removed_total",
        "description": "Total number of fish removed"
  }
  ACTIVE_FISH = {
        "name": "active_fish",
        "description": "Current number of active fish in the pond"
  }
  FISH_LOCAL = {
        "name": "fish_local",
        "description": "Number of local fish"
  }
  FISH_VISITORS = {
        "name": "fish_visitors",
        "description": "Number of visitor fish"
  }
  
