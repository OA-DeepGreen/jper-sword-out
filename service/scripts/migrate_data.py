import esprit
import logging
from service import models

"""
This script copies data from elasticsearch 2.4 with one index containing many types to
elastic search 7, with each type in its own index.

The application code has been migrated to work with elastic search 7

Query the old es index directly using esprit, and load the data into the new es using the application, to ensure the data
model is consistent.

Most of the data is copied directly from one index type to the other, except for accounts and notifications.
These are modified, as we no longer need to distinguish between standard and regular accounts.
"""


def old_es_connection():
    # Old ES data
    host = 'localhost'
    port = '9200'
    index = 'jper'
    verify_ssl = False
    index_per_type = False
    return esprit.raw.Connection(host, index, port=port, verify_ssl=verify_ssl, index_per_type=index_per_type)


def sword_repository_status_mapping():
    return {
        "properties": {
            "created_date": {
                "type": "date",
            },
            "id": {
                "type": "text",
                "fields": {
                    "exact": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    }
                }
            },
            "last_deposit_date": {
                "type": "date",
            },
            "last_tried": {
                "type": "date",
            },
            "last_updated": {
                "type": "date",
            },
            "location": {
                "type": "geo_point"
            },
            "retries": {
                "type": "long"
            },
            "status": {
                "type": "text",
                "fields": {
                    "exact": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    }
                }
            }
        }
    }


def sword_deposit_record_mapping():
    return {
        "properties": {
            "completed_status": {
                "type": "text",
                "fields": {
                    "exact": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    }
                }
            },
            "content_status": {
                "type": "text",
                "fields": {
                    "exact": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    }
                }
            },
            "created_date": {
                "type": "date",
            },
            "deposit_date": {
                "type": "date",
            },
            "id": {
                "type": "text",
                "fields": {
                    "exact": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    }
                }
            },
            "last_updated": {
                "type": "date",
            },
            "location": {
                "type": "geo_point"
            },
            "metadata_status": {
                "type": "text",
                "fields": {
                    "exact": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    }
                }
            },
            "notification": {
                "type": "text",
                "fields": {
                    "exact": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    }
                }
            },
            "repo": {
                "type": "text",
                "fields": {
                    "exact": {
                        "type": "keyword",
                        "normalizer": "lowercase"
                    }
                }
            }
        }
    }


def model_for_type(index_type):
    models_by_type = {
        'sword_deposit_record': models.DepositRecord,
        'sword_repository_status': models.RepositoryStatus
    }
    return models_by_type.get(index_type, None)


def migrate_record(conn, logging, index_type, modify_data_func=None, **func_args):
    logging.info("Starting migration of {t}".format(t=index_type))
    model_class = model_for_type(index_type)
    q = {"query": {"match_all": {}}}
    data_scroll = esprit.tasks.scroll(conn, index_type, q, page_size=1000, limit=None, keepalive="10m")
    for data in data_scroll:
        ignore = False
        if modify_data_func:
            ignore = modify_data_func(logging, data, **func_args)
        if not ignore:
            if index_type == 'sword_deposit_record':
                esprit.raw.put_mapping(conn, type=index_type, mapping=sword_deposit_record_mapping())
            elif index_type == 'sword_repository_status':
                esprit.raw.put_mapping(conn, type=index_type, mapping=sword_repository_status_mapping())
            mc = model_class(data)
            mc.save()
    logging.info("Finished migration of {t}".format(t=index_type))


def migrate_data(conn, logging, migrate_all=True, migrate_account=True, migrate_notification=True, migrate_sword=True):
    # For each type in sword_deposit_record and sword_repository_status
    # For each record in that type:
    #     create a new record of that type with the _source data and save
    if migrate_sword:
        for index_type in ['sword_deposit_record', 'sword_repository_status']:
            migrate_record(conn, logging, index_type, modify_data_func=None)
    return


if __name__ == "__main__":
    # logging
    logging.basicConfig(filename='sword_migration.log', level=logging.INFO, format='%(asctime)s %(message)s')
    conn = old_es_connection()
    migrate_data(conn, logging, migrate_sword=True)
