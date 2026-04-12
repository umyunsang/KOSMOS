# Vulture whitelist — false positives from framework patterns.
# See: https://github.com/jendrikseipp/vulture#whitelisting

# Pydantic @field_validator / @model_validator require cls as first arg
cls  # noqa: F821

# __aexit__ protocol requires *args
args  # noqa: F821
