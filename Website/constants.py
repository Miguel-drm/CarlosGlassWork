"""Constants used throughout the application"""

# Customize request status constants
CUSTOMIZE_STATUS = {
    'PENDING': 'pending',
    'APPROVED': 'approved',
    'REJECTED': 'rejected'
}

# Bootstrap color classes for status badges
STATUS_COLORS = {
    'pending': 'warning',
    'approved': 'success',
    'rejected': 'danger'
}