from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# To use this code, follow the steps here, and get the quickstart running:
# https://developers.google.com/gmail/api/quickstart/python
# Then, delete token.pickle (this script needs trash permissions), and run this file
# in the same way that quickstart.py was run

# For large numbers of messages, batchDelete is faster than trash, but unrecoverable
USE_BATCH_DELETE = False

def getMessagesWithLabels(service, user_id, label_ids, max_num_results):
    """List all Messages of the user's mailbox with label_ids applied.

    Args:
      service: Authorized Gmail API service instance.
      user_id: User's email address. The special value "me"
      can be used to indicate the authenticated user.
      label_ids: Only return Messages with these labelIds applied.

    Returns:
      List of Messages that have all required Labels applied. Note that the
      returned list contains Message IDs, you must use get with the
      appropriate id to get the details of a Message.
    """
    response = service.users().messages().list(userId=user_id,
                                               labelIds=label_ids).execute()
    messages = []
    if 'messages' in response:
        messages.extend(response['messages'])
        while 'nextPageToken' in response and len(messages) <= max_num_results:
            print('\rFound %d messages' % len(messages), end='')
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=user_id,
                                                       labelIds=label_ids,
                                                       pageToken=page_token).execute()
            messages.extend(response['messages'])
    print() # new line after carriage returns
    return messages

def get100(x):
    for i in range(0, len(x), 100):
        yield x[i:i+100]

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.

    scopes = ['https://mail.google.com/'] if USE_BATCH_DELETE else \
        ['https://www.googleapis.com/auth/gmail.modify']

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    # Call the Gmail API
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        print('No labels found.')
        return
    else:
        print('Labels:')
        for label in labels:
            print('id: ' + label['id'])
            print('    name: ' + label['name'])

    label_id = input("Enter id of label to delete: ")
    max_num_to_delete = int(input("Enter max number of emails to delete: "))

    print('Searching for emails...')
    messages = getMessagesWithLabels(service, 'me', [label_id], max_num_to_delete)
    num_to_preview = min(10, len(messages))
    print('Snippets of first ' + str(num_to_preview) + ' messages:')
    for i in range(num_to_preview):
        message = service.users().messages().get(userId='me', id=messages[i]['id']).execute()
        print ('Snippet %d: %s' % (i, message['snippet']))


    num_to_delete = min(max_num_to_delete, len(messages))
    try:
        if USE_BATCH_DELETE:
            input('\nPress enter to begin permanently deleting')
            all_message_ids = [m['id'] for m in messages[:num_to_delete]]
            divided_message_ids = list(get100(all_message_ids))
            num_deleted = 0
            for message_ids in divided_message_ids:
                service.users().messages().batchDelete(userId='me', body={'ids': message_ids}).execute()
                num_deleted += len(message_ids)
                print('\rDeleted %d/%d' % (num_deleted, num_to_delete), end='')
        else:
            input('\nPress enter to begin moving to trash')
            for i in range(num_to_delete):
                service.users().messages().trash(userId='me', id=messages[i]['id']).execute()
                print('\rDeleted %d/%d' % (i+1, num_to_delete), end='')
    except HttpError:
        print('Failed to delete - try deleting token.pickle and try again')
        return

    print('\n\nFinished')

if __name__ == '__main__':
    main()
