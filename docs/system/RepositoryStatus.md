# RepositoryStatus

The JSON structure of the model is as follows:

```json
{
    "created_date": "2015-11-25T09:18:48Z", 
    "id": "string", 
    "last_deposit_date": "2015-11-25T09:18:48Z", 
    "last_tried": "2015-11-25T09:18:48Z", 
    "last_updated": "2015-11-25T09:18:48Z", 
    "retries": 0, 
    "status": "string"
}
```

Each of the fields is defined as laid out in the table below:

| Field | Description | Datatype | Format | Allowed Values |
| ----- | ----------- | -------- | ------ | -------------- |
| created_date | Date record was created | unicode | UTC ISO formatted date: YYYY-MM-DDTHH:MM:SSZ |  |
| id | opaque record identifier | unicode |  |  |
| last_deposit_date | Last time a successful deposit was made against this repository | unicode | UTC ISO formatted date: YYYY-MM-DDTHH:MM:SSZ |  |
| last_tried | Last time a deposit was attempted against this repository, which subsequently failed | unicode | UTC ISO formatted date: YYYY-MM-DDTHH:MM:SSZ |  |
| last_updated | Date record was last modified | unicode | UTC ISO formatted date: YYYY-MM-DDTHH:MM:SSZ |  |
| retries | Number of retried deposit attempts against this repository, following a failure.  Each failure increases the retry counter until it rolls over from status "problem" to status "failing" | int |  |  |
| status | Current known status of the repository.  "problem" repositories will be retried, "failing" repositories need to be re-activated manually. | unicode |  | succeeding, failing, problem |
