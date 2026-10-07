import argparse
import logging
from pathlib import Path

from kanban.client import GitHubGraphQLClient
from kanban.exporter import CsvExporter
from kanban.fetcher import KanbanFetcher
from pipeline.config import carregar_dotenv, get_token, load_config

logger = logging.getLogger(__name__)

DEFAULT_ORG = "Laboratorio-Medicao"
DEFAULT_PROJECT_NUMBER = 1
DEFAULT_LABEL_FILTER = "lab03"
SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent / "data" / "kanban-snapshots"


def _parse_args():
    parser = argparse.ArgumentParser(description="Gera snapshot do Kanban GitHub Projects v2")
    parser.add_argument("--org", default=DEFAULT_ORG, help="organização GitHub")
    parser.add_argument("--project", type=int, default=DEFAULT_PROJECT_NUMBER, help="número do projeto")
    parser.add_argument("--label", default=DEFAULT_LABEL_FILTER, help="filtrar por label (padrão: lab03)")
    parser.add_argument("--config", default="config.yaml", help="caminho do config.yaml")
    return parser.parse_args()


def run(token, org=DEFAULT_ORG, project_number=DEFAULT_PROJECT_NUMBER,
        label_filter=DEFAULT_LABEL_FILTER, output_dir=SNAPSHOTS_DIR):
    client = GitHubGraphQLClient(token=token)
    fetcher = KanbanFetcher(client, org=org, project_number=project_number, label_filter=label_filter)
    items = fetcher.fetch_all()

    exporter = CsvExporter(output_dir)
    output_path = exporter.export(items)

    logger.info("snapshot salvo: %s (%s itens)", output_path, len(items))
    return output_path


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    carregar_dotenv()
    config = load_config(args.config)
    token = get_token(config)
    run(token=token, org=args.org, project_number=args.project, label_filter=args.label)


if __name__ == "__main__":
    main()
