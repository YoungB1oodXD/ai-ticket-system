import json

with open('workflow/7x24小时ai工单分诊自动化工作流.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

replaced = []

for node in data['nodes']:
    name = node.get('name', '')

    if 'credentials' in node:
        for cred_key in list(node['credentials'].keys()):
            cred = node['credentials'][cred_key]
            if 'id' in cred and len(cred['id']) >= 10:
                cred['id'] = '{{YOUR_OPENAI_CREDENTIAL_ID}}'
                cred['name'] = '{{YOUR_OPENAI_CREDENTIAL_NAME}}'
                replaced.append(f'{name}.{cred_key}.id')

    if node.get('type') == 'n8n-nodes-base.webhook':
        if 'credentials' in node:
            for cred_key in node['credentials']:
                node['credentials'][cred_key]['id'] = '{{YOUR_HEADER_AUTH_CREDENTIAL_ID}}'
                node['credentials'][cred_key]['name'] = '{{YOUR_HEADER_AUTH_CREDENTIAL_NAME}}'
        if 'webhookId' in node:
            node['webhookId'] = '{{YOUR_WEBHOOK_ID}}'
            replaced.append(f'{name}: webhookId')

    if name == '获取飞书Token':
        body = node['parameters']['jsonBody']
        body = body.replace('cli_aaacc610f03a1ccd', '{{YOUR_FEISHU_APP_ID}}')
        body = body.replace('C6ljehkoTpn5L63zwutHi7XabaWYzBgn', '{{YOUR_FEISHU_APP_SECRET}}')
        node['parameters']['jsonBody'] = body
        replaced.append('feishu app_id/app_secret')

    if node.get('type') == 'n8n-nodes-base.emailSend':
        node['parameters']['fromEmail'] = '{{YOUR_SMTP_FROM_EMAIL}}'
        node['parameters']['toEmail'] = '{{YOUR_SMTP_TO_EMAIL}}'
        if 'credentials' in node:
            for cred_key in node['credentials']:
                node['credentials'][cred_key]['id'] = '{{YOUR_SMTP_CREDENTIAL_ID}}'
                node['credentials'][cred_key]['name'] = '{{YOUR_SMTP_CREDENTIAL_NAME}}'
        replaced.append('SMTP config')

    if name == 'ragflow知识库检索':
        for h in node['parameters']['headerParameters']['parameters']:
            if h['name'] == 'Authorization':
                h['value'] = '{{YOUR_RAGFLOW_API_KEY}}'
        body = node['parameters']['jsonBody']
        body = body.replace('fcc34ecc68c311f1827a9b6ee29d737f', '{{YOUR_RAGFLOW_DATASET_ID}}')
        node['parameters']['jsonBody'] = body
        replaced.append('RagFlow config')

    if name == '配置多维表格ID':
        for a in node['parameters']['assignments']['assignments']:
            if a['name'] == 'app_token':
                a['value'] = '{{YOUR_FEISHU_APP_TOKEN}}'
            if a['name'] == 'table_id':
                a['value'] = '{{YOUR_FEISHU_TABLE_ID}}'
        replaced.append('feishu table config')

    if name in ['向群组发送紧急工单信息', '向群组发送常规工单信息']:
        body = node['parameters']['jsonBody']
        body = body.replace('oc_16172b556a1feeb6879b78593e3ae33d', '{{YOUR_FEISHU_CHAT_ID}}')
        node['parameters']['jsonBody'] = body
        replaced.append(f'{name}: chat_id')

    if node.get('type') == 'n8n-nodes-base.wait' and 'webhookId' in node:
        node['webhookId'] = '{{YOUR_WAIT_WEBHOOK_ID}}'

data['versionId'] = '{{VERSION_ID}}'
data['meta']['instanceId'] = '{{N8N_INSTANCE_ID}}'
data['id'] = '{{WORKFLOW_ID}}'

with open('workflow/ticket-workflow.template.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Done. Replaced items:')
for r in replaced:
    print(f'  {r}')
