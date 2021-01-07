from common.cache import Cache, IntegerField

from users.models import User, UserGroup
from assets.models import Asset
from .models import OrganizationMember


class OrgResourceCache(Cache):
    user_amount = IntegerField()
    group_amount = IntegerField()

    def __init__(self, org_id):
        self.org_id = org_id
        self.set_key_suffix(org_id)

    def compute_user_amount(self):
        user_amount = OrganizationMember.objects.values(
            'user_id'
        ).filter(org_id=self.org_id).distinct().count()
        print(f'compute_user_amount {user_amount}')
        return user_amount

    def compute_group_amount(self):
        group_amount = UserGroup.objects.filter(
            org_id=self.org_id
        ).distinct().count()
        print(f'compute_group_amount {group_amount}')
        return group_amount
