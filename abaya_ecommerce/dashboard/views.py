# dashboard/views.py
# Import and organize all view functions for easier import in urls.py

# Dashboard main views
from dashboard.views.dashboard_views import (
    dashboard_home,
)

# Category management views
from dashboard.views.category_views import (
    category_list,
    category_create,
    category_edit,
    category_delete,
)

# Product management views
from dashboard.views.product_views import (
    product_list,
    product_detail,
    product_create,
    product_edit,
    product_delete,
    product_media,
    product_media_add,
    product_media_delete,
)

# Attribute management views
from dashboard.views.attribute_views import (
    # Size views
    size_list,
    size_create,
    size_edit,
    size_delete,
    
    # Fabric views
    fabric_list,
    fabric_create,
    fabric_edit,
    fabric_delete,
    
    # Color views
    color_list,
    color_create,
    color_edit,
    color_delete,
)

# Currency management views
from dashboard.views.currency_views import (
    currency_list,
    currency_create,
    currency_edit,
    currency_delete,
)

# Order management views
from dashboard.views.order_views import (
    order_list,
    order_detail,
    order_update_status,
    sales_report,
)

# Coupon management views
from dashboard.views.coupon_views import (
    coupon_list,
    coupon_create,
    coupon_edit,
    coupon_delete,
)

# User management views
from dashboard.views.user_views import (
    user_list,
    user_detail,
    user_orders,
)

# Report views
from dashboard.views.report_views import (
    product_report,
    customer_report,
)

# Activity logs and settings views
from dashboard.views.log_views import (
    activity_logs,
    dashboard_settings,
)