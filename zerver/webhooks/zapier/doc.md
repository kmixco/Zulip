Get notifications from every event supported by Zapier.

1. {!create-stream.md!}

1. {!create-bot-construct-url-indented.md!}

1. Create a **Zap** and select the service you'd like to receive notifications
   from as the **Trigger (Step 1)**. Choose **Webhooks by Zapier** as the
   app in **Action (Step 2)**. Select **POST** as the action, and click
   **Save + Continue**.

1. Set **URL** to the URL constructed above. Set **Payload Type** to `JSON`.
   Add the following two fields to **Data**:

    * `subject` is the field corresponding to the subject of a message
    * `content` is the field corresponding to the content of a message

    Customize the `subject` and `content` fields as necessary. Click
    **Continue**.

{!congrats.md!}

![](/static/images/integrations/zapier/001.png)
