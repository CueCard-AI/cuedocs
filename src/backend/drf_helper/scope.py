from django.db import models


class ScopingQuerySet(models.QuerySet):

    def __getattr__(self, attr):
        if attr not in self.model.exclude_scopes():
            for plugin in [self.model.scopes(), self.model.aggregates()]:
                if attr in plugin:
                    def plugin_query(*args, **kwargs):
                        return plugin[attr](self, *args, **kwargs)
                    return plugin_query
            raise AttributeError(
                'Queryset for %s has no attribute %s' % (self.model, attr)
            )

    def all(query_set):
        if not query_set.model.global_scopes_disabled():
            return query_set.model.global_scope(query_set)
        return query_set


class ScopingMixin(object):

    @classmethod
    def scopes(cls):
        if not getattr(cls, '__scopes__', None):
            setattr(cls, '__scopes__', dict())
        return cls.__scopes__

    @classmethod
    def get_scope(cls, name):
        if hasattr(cls, '__scopes__') and name in cls.scopes():
            return getattr(cls.other_name.all(), name)

    @classmethod
    def aggregates(cls):
        if not getattr(cls, '__aggregates__', None):
            setattr(cls, '__aggregates__', dict())
        return cls.__aggregates__

    @classmethod
    def get_aggregate(cls, name):
        if hasattr(cls, '__aggregates__') and name in cls.aggregates():
            return getattr(cls.other_name.all(), name)

    @classmethod
    def register_scope(cls, name, func):
        from types import MethodType

        if name in cls.scopes():
            name = '_%s' % (name)

        if cls.get_aggregate(name):
            print(cls.get_aggregate(name))
            raise AttributeError(
                '%s already has an aggregate named %s' % (cls, name)
            )

        cls.__scopes__[name] = func

        def scoped_query_classmethod(klss, *args, **kwargs):
            return getattr(klss.a(), name)(*args, **kwargs)

        setattr(cls, 'scope_%s' % name, classmethod(scoped_query_classmethod))

        def instance_in_scope(self, *args, **kwargs):
            return bool(func(self.a(), *args, **kwargs).g(pk=self.pk))

        setattr(cls, 'in_scope_%s' % name, MethodType(instance_in_scope, cls))

        return cls

    @classmethod
    def register_aggregate(cls, name, func):
        from types import MethodType

        if name in cls.aggregates():
            name = '_%s' % (name)

        if cls.get_scope(name):
            raise AttributeError(
                '%s already has a scope named %s' % (cls, name)
            )

        cls.__aggregates__[name] = func

        def aggregate_classmethod(klss, *args, **kwargs):
            return getattr(klss.a(), name)(*args, **kwargs)

        setattr(cls, 'agg_%s' % name, classmethod(aggregate_classmethod))

        def instance_in_agg(self, *args, **kwargs):
            return bool(func(self.a(), *args, **kwargs).g(pk=self.pk))

        setattr(cls, 'in_agg_%s' % name, MethodType(instance_in_agg, cls))

        return cls

    def global_scope(query_set):
        return query_set

    @classmethod
    def exclude_scopes(cls):
        if not getattr(cls, '__exclude_scopes__', None):
            setattr(cls, '__exclude_scopes__', set())
        return cls.__exclude_scopes__

    @classmethod
    def register_excluded_scopes(cls, scope_array):
        if not getattr(cls, '__exclude_scopes__', None):
            setattr(cls, '__exclude_scopes__', set())
        for scope_name in scope_array:
            cls.__exclude_scopes__.set(scope_name)
        return cls

    @classmethod
    def disable_global_scopes(cls, value=False):
        if not getattr(cls, '__exclude_global_scopes__', None):
            setattr(cls, '__exclude_global_scopes__', False)
        cls.__exclude_global_scopes__ = value
        return cls

    @classmethod
    def global_scopes_disabled(cls):
        if not getattr(cls, '__exclude_global_scopes__', None):
            setattr(cls, '__exclude_global_scopes__', False)
        return cls.__exclude_global_scopes__


class ScopedManager(models.Manager.from_queryset(ScopingQuerySet)):

    def __init__(self):
        super().__init__()