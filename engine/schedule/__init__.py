# AS 1288 Glass Thickness Calculator
# engine/schedule/__init__.py
#
# Window Schedule translation layer - pure geometry-to-ctx translation from
# a Configurator export into the inputs engine/human_impact expects.
#
# Standalone layer - must never import from engine/wind_load,
# engine/silicone_bite, or engine/combined. May be imported by tests that
# also exercise engine/human_impact directly for integration checks.
#
# Duce Timber Windows and Doors

from engine.schedule.translation import translate_pane, translate_system

__all__ = ['translate_pane', 'translate_system']
