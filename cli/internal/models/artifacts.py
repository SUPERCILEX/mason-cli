import abc
from abc import abstractmethod

import six


@six.add_metaclass(abc.ABCMeta)
class IArtifact:
    @abstractmethod
    def validate(self):
        pass

    @abstractmethod
    def log_details(self):
        pass

    @abstractmethod
    def get_content_type(self):
        pass

    @abstractmethod
    def get_type(self):
        pass

    @abstractmethod
    def get_pretty_type(self):
        pass

    @abstractmethod
    def get_sub_type(self):
        pass

    @abstractmethod
    def get_name(self):
        pass

    @abstractmethod
    def get_version(self):
        pass

    @abstractmethod
    def get_registry_meta_data(self):
        pass

    @abstractmethod
    def __eq__(self, other):
        pass

    def __repr__(self):
        return '{}({})'.format(
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )
