"""
Settings for Biz
"""
import tempfile


"""
Basic settings
"""
# Dummy biz secret key for dev/test
BIZ_SECRET_KEY = 'test'

"""
Batch Settings
"""
BIZ_SET_SCORE_COMMAND_OUTPUT = tempfile.NamedTemporaryFile().name
BIZ_SET_PLAYBACK_COMMAND_OUTPUT = tempfile.NamedTemporaryFile().name

"""
Monthly report info
"""
BIZ_MONTHLY_REPORT_COMMAND_OUTPUT = tempfile.NamedTemporaryFile().name
BIZ_FROM_EMAIL = 'from@test.com'
BIZ_RECIPIENT_LIST = ['recipient@test.com']
