# Report Architecture

## 1. Related Repositories

- **Missive conversation sidebar**
  - https://github.com/PublicDataWorks/txt-outlier-convo-sidebar
- **Missive broadcast sidebar**
  - https://github.com/PublicDataWorks/txt-outlier-frontend
- **Broadcast backend**
  - https://github.com/PublicDataWorks/txt-outlier-backend
- **Lookup backend**
  - https://github.com/PublicDataWorks/txt-outlier-lookups

## 2. Config Variables Description

### Variable Descriptions

1. `all_good`: A message sent when the user is finished with their inquiry.

2. `no_match`: A response when an address cannot be found in the database.

3. `wrong_format`: A message sent when the user inputs an address in an unrecognizable format.

4. `closest_match`: A message asking for confirmation when a similar address is found.

5. `return_info`: The main response containing property information.

6. `return_info2`: A follow-up message offering additional assistance.

7. `has_tax_debt`: Message provided when a property has tax debt.

8. `unregistered`: Message about unregistered rental properties.

9. `registered`: Message about registered rental properties.

10. `foreclosed`: Message for properties in foreclosure.

11. `forfeited`: Message for properties in forfeiture.

12. `final`: A closing message offering further assistance.

13. `match_second_message`: A follow-up message after providing property information.

14. `not_in_session`: A message indicating the user needs to start a lookup session.

15. `search_prompt`: Prompt for look-up LLM model to search.

16. `search_context`: Context and instructions for LLM to query the property database.

17. `search_context_with_sunit`: Similar to `search_context`, but includes unit information.

18. `land_bank`: Message about land bank properties.

19. `tax_unconfirmed`: Explanation of "unconfirmed" tax status.

20. `sms_history_summary`: Prompt for summary LLM to generate SMS conversation history.

21. `missive_report_conversation_id`: ID for the weekly report conversation in Missive.

22. `comment_summary_prompt`: Prompt for LLM model to summarize reporter comments.

23. `impact_summary_prompt`: Prompt for LLM model to summarize conversation outcomes and impact.

24. `message_summary_prompt`: Prompt for LLM model to summarize user communication patterns.

25. `keyword_label_parent_id`: ID for the parent label of keyword categories.

26. `impact_label_parent_id`: ID for the parent label of impact categories.

27. `max_tokens`: Maximum number of tokens for AI model responses.

28. `search_model`: The AI model used for search queries.

29. `summary_model`: The AI model used for generating summaries.

30. `outcome_title`: Title for the impact and outcomes section in convo sidebar.

31. `comments_title`: Title for the reporter notes section in convo sidebar.

32. `messages_title`: Title for the communication patterns section in convo sidebar.

33. `number of recipients for each batch`: Update the `no_users` column in the `broadcasts` table for the most recent broadcast (the one with the largest `id`)

## 3. Deploy Steps:
### Full Flow of Deploying Backend

#### 1. AWS Console Access and Security Group Configuration

1. Log in to the AWS Management Console.
2. Navigate to the EC2 service.
3. In the left sidebar, under "Network & Security," click on "Security Groups."
4. Find and select the security group associated with your EC2 instance:
5. In the bottom pane, click on the "Inbound rules" tab.
6. Click the "Edit inbound rules" button.
7. Click "Add rule."
8. For the new rule, set the following:
   - Type: SSH
   - Protocol: TCP
   - Port Range: 22
   - Source: Custom
9. In the text box next to "Custom," enter the IP address you want to whitelist. Add "/32" at the end to specify a single IP (e.g., "203.0.113.0/32").
10. (Optional) Add a description for the rule to help you remember why it was added.
11. Click "Save rules" to apply the changes.

#### 2. Connecting to EC2 Instance

1. Request the pem file from developers/admins.
2. Use this command to connect:
```
ssh -i PEM_FILE EC2_IP_ADDRESS
```

#### 3. Accessing Tmux Instances

Once inside the EC2 instance, check for 2 tmux instances:

1. Backend instance (broadcaster deno backend):
   ```
   tmux a -t backend
   ```

2. Lookup instance (address lookup/conversation summary python backend):
   ```
   tmux a -t lookup
   ```

#### 4. Deploying Backend

[Lookup](https://github.com/PublicDataWorks/txt-outlier-lookups?tab=readme-ov-file#docker-quick-start)



### 4. Migrations and database schema
Refer to [user-actions](https://github.com/PublicDataWorks/txt-outlier-import/tree/main/supabase/functions/user-actions/drizzle) for more information

### Important Note on Environment Variables
🔐 **Security Notice**: 
All environment variables and sensitive configuration data mentioned in this document are securely stored in 1Password. For access to these variables, please refer to the project's vault in 1Password. Never share these credentials openly or store them in unsecured locations.
