from django.core.cache import cache

from common.utils import get_logger

logger = get_logger(__file__)


class CacheFieldBase:
    field_type = str

    def __init__(self, timeout=None, compute_func_name=None):
        self.timeout = timeout
        self.compute_func_name = compute_func_name


class StringField(CacheFieldBase):
    field_type = str


class IntegerField(CacheFieldBase):
    field_type = int


class CacheBase(type):
    def __new__(cls, name, bases, attrs: dict):
        to_update = {}
        field_descs = []

        for k, v in attrs.items():
            if isinstance(v, CacheFieldBase):
                desc = CacheValueDesc(k, v)
                to_update[k] = desc
                field_descs.append(desc)

        attrs.update(to_update)
        attrs['field_descs'] = field_descs
        return type.__new__(cls, name, bases, attrs)


class Cache(metaclass=CacheBase):
    key_suffix: str
    field_descs: list

    def refresh(self, *fields):
        if not fields:
            field_desc: CacheValueDesc

            for field_desc in self.field_descs:
                field_desc.refresh(self)
        else:
            for field in fields:
                field_desc = getattr(self.__class__, field)
                field_desc.refresh(self)

    def set_key_suffix(self, *args):
        enfore_str = []
        for arg in args:
            if not isinstance(arg, str):
                arg = str(arg)
            enfore_str.append(arg)

        self.key_suffix = '.'.join(enfore_str)


class CacheValueDesc:
    def __init__(self, field_name, field_type: CacheFieldBase):
        self.field_name = field_name
        self.field_type = field_type

    def __repr__(self):
        clz = self.__class__
        return f'<{clz.__name__} {self.field_name} {self.field_type}>'

    def __get__(self, instance: Cache, owner):
        key = self.cache_key(instance)
        value = cache.get(key)
        if value is None:
            # 缓存中没有数据时，去数据库获取
            value = self.get_new_value(instance)
            self.set_new_value(key, value)
        else:
            # 将缓存中拿到的数据进行类型转换
            value = self.field_type.field_type(value)
        return value

    def cache_key(self, instance: Cache):
        clz = instance.__class__
        key = f'cache.{clz.__module__}.{clz.__name__}.{self.field_name}.{instance.key_suffix}'
        return key

    def get_new_value(self, instance: Cache):
        compute_func_name = self.field_type.compute_func_name
        if not compute_func_name:
            compute_func_name = f'compute_{self.field_name}'
        compute_func = getattr(instance, compute_func_name, None)
        assert compute_func is not None, \
            f'Define `{compute_func_name}` method in {instance.__class__}'
        new_value = compute_func()
        return new_value

    def set_new_value(self, key, value):
        cache.set(key, value, timeout=self.field_type.timeout)
        logger.info(f'refresh_cache: {key}')

    def refresh(self, instance: Cache):
        key = self.cache_key(instance)
        new_value = self.get_new_value(instance)
        self.set_new_value(key, new_value)


# For test
#
# class OrgResource(Cache):
#     user_amount = IntegerField(timeout=None, compute_func_name=None)
#
#     def __init__(self, org_id):
#         self.org_id = org_id
#         self.set_key_suffix(org_id)
#     def compute_user_amount(self):
#         return 10
