# 新增销售单状态字段；存量销售单视为已完成，避免被取消/重复结算。

from django.db import migrations, models


def mark_existing_sales_completed(apps, schema_editor):
    Sale = apps.get_model('inventory', 'Sale')
    Sale.objects.filter(status='DRAFT').update(status='COMPLETED')


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0010_product_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='status',
            field=models.CharField(
                choices=[
                    ('DRAFT', '未完成'),
                    ('COMPLETED', '已完成'),
                    ('CANCELLED', '已取消'),
                ],
                default='DRAFT',
                max_length=20,
                verbose_name='状态',
            ),
        ),
        migrations.RunPython(mark_existing_sales_completed, migrations.RunPython.noop),
    ]
