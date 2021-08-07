# DepositRecord

The JSON structure of the model is as follows:

```json
{
    "completed_status": "string", 
    "content_status": "string", 
    "created_date": "2015-11-25T09:18:48Z", 
    "deposit_date": "2015-11-25T09:18:48Z", 
    "id": "string", 
    "last_updated": "2015-11-25T09:18:48Z", 
    "metadata_status": "string", 
    "notification": "string", 
    "repository": "string"
}
```

Each of the fields is defined as laid out in the table below:

| Field | Description | Datatype | Format | Allowed Values |
| ----- | ----------- | -------- | ------ | -------------- |
| completed_status | What is the status of the "complete" request against the repository.  If no binary content, this request will not be issued, and the value will be "none". | unicode |  | deposited, failed, none |
| content_status | What is the status of the binary content request against the repository.  If no binary content, this request will not be issued, and the value will be "none" | unicode |  | deposited, failed, none |
| created_date | Date record was created | unicode | UTC ISO formatted date: YYYY-MM-DDTHH:MM:SSZ |  |
| deposit_date | Date of this deposit | unicode | UTC ISO formatted date: YYYY-MM-DDTHH:MM:SSZ |  |
| id | opaque record identifier | unicode |  |  |
| last_updated | Date record was last modified | unicode | UTC ISO formatted date: YYYY-MM-DDTHH:MM:SSZ |  |
| metadata_status | What is the status of the metadata deposit request against the repository. | unicode |  | deposited, failed |
| notification | Notification id to which this record pertains | unicode |  |  |
| repository | Repository account id to which this record pertains | unicode |  |  |
