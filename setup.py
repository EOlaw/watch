import asyncio
import logging
from src.core.system_interface.main_controller import MainController

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def main():
    try:
        controller = MainController()
        initialization_success = await controller.initialize_system()
        if not initialization_success:
            logger.error("System initialization failed")
            return

        while True:
            status = await controller.update_system_status()
            logger.info(f"System Status: {status}")
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("\nInitiating system shutdown...")
        await controller.shutdown()
    except Exception as e:
        logger.error(f"System error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())