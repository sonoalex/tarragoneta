"""
Dependency Injection Container for Tarracograf
Simple DI container for managing dependencies with type hint support
"""
from typing import Any, Callable, Dict, Type, TypeVar, Optional, get_type_hints, get_origin, get_args
from functools import wraps
import inspect

T = TypeVar('T')


class Container:
    """Simple dependency injection container with type hint support"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._type_registry: Dict[Type, str] = {}  # Map type -> service name
    
    def register(self, name: str, factory: Callable, singleton: bool = True, service_type: Optional[Type] = None):
        """
        Register a service factory
        
        Args:
            name: Service name (e.g., 'email_provider')
            factory: Factory function that creates the service instance
            singleton: If True, the service will be created once and reused
            service_type: Optional type hint for the service (for type-based injection)
        """
        self._factories[name] = factory
        # Store singleton flag
        self._services[name] = {'singleton': singleton}
        
        # Register type mapping if provided
        if service_type:
            self._type_registry[service_type] = name
    
    def register_instance(self, name: str, instance: Any, service_type: Optional[Type] = None):
        """
        Register a pre-created instance
        
        Args:
            name: Service name
            instance: Pre-created instance
            service_type: Optional type hint for the service
        """
        self._singletons[name] = instance
        if service_type:
            self._type_registry[service_type] = name
    
    def get(self, name: Optional[str] = None, service_type: Optional[Type] = None) -> Any:
        """
        Get a service instance by name or type
        
        Args:
            name: Service name (if provided)
            service_type: Service type (if provided, will look up by type)
            
        Returns:
            Service instance
        """
        # If type is provided, try to find service name
        if service_type and not name:
            name = self._type_registry.get(service_type)
            if not name:
                # Try to find by checking if any registered type matches
                for reg_type, reg_name in self._type_registry.items():
                    if self._is_subtype(service_type, reg_type):
                        name = reg_name
                        break
                if not name:
                    raise ValueError(f'No service registered for type {service_type}')
        
        if not name:
            raise ValueError('Either name or service_type must be provided')
        
        # Check if it's already a singleton instance
        if name in self._singletons:
            return self._singletons[name]
        
        # Check if we have a factory
        if name not in self._factories:
            raise ValueError(f'Service "{name}" is not registered')
        
        factory = self._factories[name]
        
        # Create instance
        instance = factory()
        
        # Cache if singleton
        service_config = self._services.get(name, {})
        if service_config.get('singleton', True):
            self._singletons[name] = instance
        
        return instance
    
    def _is_subtype(self, subtype: Type, basetype: Type) -> bool:
        """Check if subtype is a subclass of basetype"""
        try:
            return issubclass(subtype, basetype)
        except TypeError:
            return False
    
    def has(self, name: Optional[str] = None, service_type: Optional[Type] = None) -> bool:
        """Check if a service is registered"""
        if service_type and not name:
            name = self._type_registry.get(service_type)
        if name:
            return name in self._factories or name in self._singletons
        return False


# Global container instance
_container = Container()


def get_container() -> Container:
    """Get the global DI container"""
    return _container


def inject(*dependencies):
    """
    Decorator to inject dependencies into a function using type hints
    
    Usage:
        @inject()
        def my_function(email_provider: EmailProvider, other_service: OtherService):
            ...
        
        Or with explicit names:
        @inject('email_provider', 'other_service')
        def my_function(email_provider, other_service):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Get type hints from function signature
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            container = get_container()
            injected_kwargs = {}
            
            # If explicit dependencies are provided, use them
            if dependencies:
                for dep_name in dependencies:
                    if dep_name in kwargs:
                        continue  # Already provided
                    service = container.get(dep_name)
                    injected_kwargs[dep_name] = service
            else:
                # Auto-inject based on type hints
                for param_name, param in sig.parameters.items():
                    # Skip if already provided or is self/cls
                    if param_name in kwargs or param_name in ('self', 'cls'):
                        continue
                    
                    # Skip positional-only or var args
                    if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                        continue
                    
                    # Get type hint for this parameter
                    param_type = type_hints.get(param_name)
                    if param_type:
                        try:
                            service = container.get(service_type=param_type)
                            injected_kwargs[param_name] = service
                        except ValueError:
                            # Service not found for this type, skip it
                            pass
            
            # Merge injected kwargs with provided kwargs
            kwargs.update(injected_kwargs)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def provide(name: Optional[str] = None, service_type: Optional[Type] = None) -> Any:
    """
    Function to get a service from the container by name or type
    
    Usage:
        # By name
        email_provider = provide('email_provider')
        
        # By type (if registered with type)
        email_provider = provide(service_type=EmailProvider)
    """
    return get_container().get(name=name, service_type=service_type)

