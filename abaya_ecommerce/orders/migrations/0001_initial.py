# Generated by Django 5.2 on 2025-04-24 10:27

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Coupon',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=50, unique=True)),
                ('type', models.CharField(choices=[('PERCENTAGE', 'Percentage'), ('FIXED', 'Fixed Amount')], max_length=10)),
                ('value', models.DecimalField(decimal_places=2, max_digits=10)),
                ('min_order_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('max_discount_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('usage_limit', models.PositiveIntegerField(blank=True, null=True)),
                ('usage_count', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Coupon',
                'verbose_name_plural': 'Coupons',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('order_number', models.CharField(max_length=50, unique=True)),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=10)),
                ('shipping_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tax_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('notes', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('SHIPPED', 'Shipped'), ('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled'), ('REFUNDED', 'Refunded'), ('ON_HOLD', 'On Hold'), ('COMPLETED', 'Completed')], default='PENDING', max_length=20)),
                ('payment_status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed'), ('REFUNDED', 'Refunded'), ('PARTIALLY_REFUNDED', 'Partially Refunded')], default='PENDING', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Order',
                'verbose_name_plural': 'Orders',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('quantity', models.PositiveIntegerField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Order Item',
                'verbose_name_plural': 'Order Items',
            },
        ),
        migrations.CreateModel(
            name='OrderStatusLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('SHIPPED', 'Shipped'), ('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled'), ('REFUNDED', 'Refunded'), ('ON_HOLD', 'On Hold'), ('COMPLETED', 'Completed')], max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.CharField(blank=True, max_length=100, null=True)),
            ],
            options={
                'verbose_name': 'Order Status Log',
                'verbose_name_plural': 'Order Status Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('payment_method', models.CharField(choices=[('CREDIT_CARD', 'Credit Card'), ('DEBIT_CARD', 'Debit Card'), ('UPI', 'UPI'), ('NET_BANKING', 'Net Banking'), ('WALLET', 'Wallet'), ('COD', 'Cash on Delivery'), ('BANK_TRANSFER', 'Bank Transfer')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(max_length=3)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed'), ('REFUNDED', 'Refunded'), ('PARTIALLY_REFUNDED', 'Partially Refunded')], default='PENDING', max_length=20)),
                ('transaction_id', models.CharField(blank=True, max_length=255, null=True)),
                ('payment_gateway', models.CharField(blank=True, max_length=100, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Payment',
                'verbose_name_plural': 'Payments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Return',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('return_number', models.CharField(max_length=50, unique=True)),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('REQUESTED', 'Requested'), ('APPROVED', 'Approved'), ('RECEIVED', 'Received'), ('REJECTED', 'Rejected'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')], default='REQUESTED', max_length=20)),
                ('refund_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('refund_status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed'), ('CANCELLED', 'Cancelled')], default='PENDING', max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Return',
                'verbose_name_plural': 'Returns',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReturnItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('quantity', models.PositiveIntegerField()),
                ('reason', models.TextField(blank=True, null=True)),
                ('condition', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Return Item',
                'verbose_name_plural': 'Return Items',
            },
        ),
        migrations.CreateModel(
            name='ReturnLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('REQUESTED', 'Requested'), ('APPROVED', 'Approved'), ('RECEIVED', 'Received'), ('REJECTED', 'Rejected'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')], max_length=20)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_by', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Return Log',
                'verbose_name_plural': 'Return Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Shipment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tracking_number', models.CharField(blank=True, max_length=100, null=True)),
                ('carrier', models.CharField(blank=True, max_length=100, null=True)),
                ('status', models.CharField(choices=[('PROCESSING', 'Processing'), ('READY_FOR_PICKUP', 'Ready for Pickup'), ('PICKED_UP', 'Picked Up'), ('IN_TRANSIT', 'In Transit'), ('OUT_FOR_DELIVERY', 'Out for Delivery'), ('DELIVERED', 'Delivered'), ('FAILED_DELIVERY', 'Failed Delivery'), ('RETURNED', 'Returned')], default='PROCESSING', max_length=20)),
                ('estimated_delivery', models.DateTimeField(blank=True, null=True)),
                ('actual_delivery', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Shipment',
                'verbose_name_plural': 'Shipments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ShipmentLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('PROCESSING', 'Processing'), ('READY_FOR_PICKUP', 'Ready for Pickup'), ('PICKED_UP', 'Picked Up'), ('IN_TRANSIT', 'In Transit'), ('OUT_FOR_DELIVERY', 'Out for Delivery'), ('DELIVERED', 'Delivered'), ('FAILED_DELIVERY', 'Failed Delivery'), ('RETURNED', 'Returned')], max_length=20)),
                ('location', models.CharField(blank=True, max_length=255, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Shipment Log',
                'verbose_name_plural': 'Shipment Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CouponCategory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('category_id', models.UUIDField()),
                ('coupon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='orders.coupon')),
            ],
            options={
                'verbose_name': 'Coupon Category',
                'verbose_name_plural': 'Coupon Categories',
            },
        ),
        migrations.CreateModel(
            name='CouponProduct',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('product_id', models.UUIDField()),
                ('coupon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='orders.coupon')),
            ],
            options={
                'verbose_name': 'Coupon Product',
                'verbose_name_plural': 'Coupon Products',
            },
        ),
    ]
