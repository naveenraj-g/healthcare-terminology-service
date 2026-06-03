from dependency_injector import containers, providers
from app.di.core import CoreContainer
from app.di.modules.terminology import TerminologyContainer


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app"])

    core = providers.Container(CoreContainer)

    terminology = providers.Container(
        TerminologyContainer,
        core=core,
    )
