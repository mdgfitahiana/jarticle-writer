test commit

Now, for the dataframe.
Make it such that there is a column at the end called "relevant_info" or something like that, that is a json like 
```json
{
    "event": "the republic president announced ...",
    "actors": [...],
    "key_numbers": [
        {
          "value" : 3000.0,
          "unit": "USD",
          "description": "price of ..."
         }
    ]
    "others" : [...]
}
```