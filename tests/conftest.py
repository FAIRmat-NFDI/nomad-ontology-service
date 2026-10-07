from nomad.config import config

# Outside a running NOMAD, plugin entry points have to be loaded explicitly.
config.load_plugins()
