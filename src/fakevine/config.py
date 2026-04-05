from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    envvar_prefix='FAKEVINE',
    load_dotenv=True,
    settings_files=['defaults.toml', 'settings.toml'],
    validators=[
        # Ensure some parameter meets a condition
        Validator("LISTEN_INTERFACE", cast=str),
        Validator("LISTEN_PORT", cast=int),
        Validator("API_KEYS", default=[]),
        Validator("LOG_FILE_NAME", cast=str),
        Validator("LOG_FILE_ENABLE", cast=bool),
        Validator("LOG_ROTATION"),
        Validator("LOG_RETENTION"),
        Validator("FAILURE_FILE", cast=str),
        Validator("COMIC_TRUNK", cast=str),
        Validator("LOCALCVDB_PATH", cast=str),
        Validator("STATICDB_PATH", cast=str),
        Validator("CACHE_CV_API_KEY", cast=str, default=None),
        Validator("CACHE_CV_API_URL", cast=str),
        Validator("CACHE_CV_UA", cast=str),
        # Only the first ValidationError will be raised
        Validator("CACHE_EXPIRY_MINUTES", cast=int, gte=-1),
        Validator("CACHE_EXPIRY_OVERRIDE", cast=dict, default={}),
    ],
)
