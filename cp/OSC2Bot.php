<?php

namespace Custom\Controllers;
use RightNow\Utils\Framework,
    RightNow\Utils\Text,
    RightNow\Libraries\ResponseObject;

class QuiqBot extends \RightNow\Controllers\Base
{
  const messages = array(
    'promptOrderNumber' => "Thanks for contacting Pella.  What PO are you inquiring on today?",
    'promptOrderAgain' => "Could I please get your PO number?",
    'orderNotFound' =>
      "We were unable to find the order for the PO that you entered, please check your order number and try again.  If you don’t have a valid PO number please contact 866-59-PELLA.\nWould you like to try entering the PO number again?",
    'orderFound' => 'The following is information tied to the PO you entered',
    'connectToAgent' => "You are being transfered to a live agent. One moment.",
    'yes' => 'Yes',
    'no' => "No"
  );
  
  //This is the constructor for the custom controller. Do not modify anything within
  //this function.
  function __construct()
  {
    parent::__construct();
  }

  private function log($message, $title = 'LOG')
  {
    error_log(print_r('-------------' . $title . '------------', true));
    error_log(print_r($message, true));
    error_log(print_r('-------------' . $title . '------------', true));
  }

  public function receive()
  {
    $appId = '025b8d46-c38e-4e71-875d-064b35b0696c';
    $appSecret =
      'eyJhbGciOiJIUzI1NiIsImtpZCI6ImJhc2ljOjAifQ.eyJ0ZW5hbnQiOiJvc2MyLXFhIiwic3ViIjoiODAwIn0.xLZ-CI61UPulh--JJ7FUxqsElQdvmc6wKBOMl6PwZ6M';
    $hookSecret = '3a94d071-85b0-45ab-bac3-9d3009eaf4a7';
    $site = 'https://osc2-qa.goquiq.com';

    $headers = apache_request_headers();

    if ($headers['X-Centricient-Hook-Token'] !== $hookSecret) {
      header($_SERVER['SERVER_PROTOCOL'] . ' 403 Unauthorized');
      Framework::writeContentWithLengthAndExit(json_encode(Config::getMessage(END_REQS_BODY_REQUESTS_FORMATTED_MSG)) . str_repeat("\n", 512), 'application/json');
      exit();
    }

    $raw_post = trim(file_get_contents('php://input'));

    $data = json_decode($raw_post, true);

    if (!$data) {
      header($_SERVER['SERVER_PROTOCOL'] . ' 400 Bad Request');
      // Pad the error message with spaces so IE will actually display it instead of a misleading, but pretty, error message.
      Framework::writeContentWithLengthAndExit(json_encode(Config::getMessage(END_REQS_BODY_REQUESTS_FORMATTED_MSG)) . str_repeat("\n", 512), 'application/json');
    }

    if ($data['ping']) {
      $this->qApiPong($site, $appId, $appSecret);
    }

    foreach ($data['conversationUpdates'] as $update) {
      $this->conversationUpdateHandler($site, $appId, $appSecret, $update);
    }
  }

  private function conversationUpdateHandler($site, $appId, $appSecret, $update)
  {
    $conversationState = $update['state'];
    $conversationId = $update['state']['id'];
    $conversationHints = $update['hints'];
    $conversationAckId = $update['ackId'];
    $botState = $update['clientState'];

    try {
      $this->reactToConversationUpdate($site, $appId, $appSecret, $conversationState, $conversationHints, $botState);
    } catch (Exception $e) {
      // do nothing
    }

    $request = json_encode(array('ackId' => $conversationAckId, 'clientState' => $botState));
    $this->qApiAcknowledge($site, $appId, $appSecret, $conversationId, $request);
  }

  private function reactToConversationUpdate($site, $appId, $appSecret, $conversation, $conversationHints, &$botState)
  {
    $hints = array();
    foreach ($conversationHints as $hint) {
      array_push($hints, $hint['hint']);
    }

    $conversationId = $conversation['id'];

    if (in_array('invitation-timer-active', $hints)) {
      $this->qApiAccept($site, $appId, $appSecret, $conversationId);
    } elseif (in_array('response-timer-active', $hints) or in_array('no-message-since-assignment', $hints)) {
      $this->generateResponse($site, $appId, $appSecret, $conversation, $botState);
    }
  }

  private function qApiPong($site, $appId, $appSecret)
  {
    $this->doCurlPost($appId, $appSecret, "$site/api/v1/agent-hooks/pong", json_encode(array('healthy' => true)));
  }

  private function qApiAcknowledge($site, $appId, $appSecret, $conversationId, $request)
  {
    $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/acknowledge", $request);
  }

  private function qApiAccept($site, $appId, $appSecret, $conversationId) {
    $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/accept", '');
  }

  private function qApiClose($site, $appId, $appSecret, $conversationId)
  {
    $this->doCurlPost($appId, $appSecret, "$site/api/v1/messaging/conversations/$conversationId/close", '');
  }

  private function qApiSendMessage($site, $appId, $appSecret, $conversationId, $request)
  {
    $this->doCurlPost(
      $appId,
      $appSecret,
      "$site/api/v1/messaging/conversations/$conversationId/send-message",
      $request
    );
  }

  private function qApiSendToQueue($site, $appId, $appSecret, $conversationId, $request)
  {
    $this->doCurlPost(
      $appId,
      $appSecret,
      "$site/api/v1/messaging/conversations/$conversationId/send-to-queue",
      $request
    );
  }

  private function qApiUpdateFields($site, $appId, $appSecret, $conversationId, $request)
  {
    $this->doCurlPost(
      $appId,
      $appSecret,
      "$site/api/v1/messaging/conversations/$conversationId/update-fields",
      $request
    );
  }

  // TODO: UPDATE ME
  private function fetchOrder($site, $appId, $appSecret, $conversationId, $orderNumber)
  {
    if (strpos($orderNumber, '0000') !== false) {
      return array(
        'CustomerNum' => '79',
        'CustomerName' => 'CARTER LUMBER',
        'CustomerStoreNum' => '236',
        'PO_Number' => '236060918',
        'OrderNumber' => 'P791758754',
        'OrderDate' => '8/28/2019',
        'PromiseDate' => '9/16/2019',
        'ShipDate' => '8/30/2019',
        'BillOfLading' => '355478-1680',
        'Carrier' => 'PBPC',
        'OrderedStatus' => 'NULL'
      );
    }

    return null;
  }

  // TODO: UPDATE ME
  private function fetchCustomer($site, $appId, $appSecret, $conversationId, $request)
  {
    return array(
      'id' => '123456',
      'name' => 'Bob Hope'
    );
  }

  private function getOrderNumber($text)
  {
    // TODO: Validate and get order number out of it
    return $text;
  }

  private function getLastMessage($conversation)
  {
    $customerMessages = array_filter($conversation['messages'], function ($message) {
      return $message['fromCustomer'];
    });

    return strtolower(end($customerMessages)['text']);
  }

  private function doCurlPost($appId, $appSecret, $url, $payload)
  {
       load_curl();

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
    curl_setopt($ch, CURLOPT_USERPWD, $appId . ':' . $appSecret);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, 0);
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $res = curl_exec($ch);

    curl_close($ch);
  }

  private function generateResponse($site, $appId, $appSecret, $conversation, &$botState)
  {
    if ($botState['last-action'] === 'prompt-order-number') {
      $this->promptOrderNumberResponseHandler($site, $appId, $appSecret, $conversation, $botState);
    } elseif ($botState['last-action'] === 'request-human') {
      $this->requestHumanResponseHandler($site, $appId, $appSecret, $conversation, $botState);
    } else {
      $this->promptOrderNumber($site, $appId, $appSecret, $conversation, $botState);
    }
  }

  // Prompt Order Action
  private function promptOrderNumber($site, $appId, $appSecret, $conversation, &$botState)
  {
    if (in_array('introduced', $botState)) {
      $firstTime = !$botState['introduced'];
    } else {
      $firstTime = true;
    }

    if ($firstTime) {
      $text = self::messages['promptOrderNumber'];
      $botState['introduced'] = true;
    } else {
      $text = self::messages['promptOrderAgain'];
    }

    $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => $text)));
    $botState['last-action'] = 'prompt-order-number';
  }

  // Prompt Order Response Handler
  private function promptOrderNumberResponseHandler($site, $appId, $appSecret, $conversation, &$botState)
  {
    $phoneNumber = '+00001929192'; // TODO: UPDATE ME;
    $order = $this->fetchOrder(
      $site,
      $appId,
      $appSecret,
      $conversation,
      $this->getOrderNumber($this->getLastMessage($conversation))
    );
    $customer = $this->fetchCustomer($site, $appId, $appSecret, $conversation, $phoneNumber);

    if (!is_null($customer) && !is_null($order)) {
      $text = self::messages['orderFound'] . "\na) PO# ". $order['PO_Number'] . "\nb) Date Ordered: " . $order['OrderDate'] . "\nc) Store # " . $order['CustomerStoreNum'] . "\nd) Confirmation # " . $order['OrderNumber'] . "\ne) Unknown" . "\nf) Estimated Delivery Date: " . $order['PromiseDate'] . "\ng) If your estimated delivery date has elapsed, please check with your receiving department";
      $this->qApiSendMessage($site, $appId, $appSecret, $conversation['id'], json_encode(array('text' => $text)));
      $this->qApiClose($site, $appId, $appSecret, $conversation['id']);
    } else {
      $this->requestHuman($site, $appId, $appSecret, $conversation, $botState);
    }
  }

  // Request Human Action
  private function requestHuman($site, $appId, $appSecret, $conversation, &$botState)
  {
    $replies = array('replies' => array(array('text' => self::messages['yes']), array('text' => self::messages['no'])));
    $text = self::messages['orderNotFound'];
    $this->qApiSendMessage(
      $site,
      $appId,
      $appSecret,
      $conversation['id'],
      json_encode(array('text' => $text, 'quiqReply' => $replies))
    );
    $botState['last-action'] = 'request-human';
  }

  // Request Human Response Handler
  private function requestHumanResponseHandler($site, $appId, $appSecret, $conversation, &$botState)
  {
    $text = strtolower($this->getLastMessage($conversation));
    $tryAgain = strtolower(self::messages['yes']);

    if (strpos($text, $yes) !== false) {
      $this->promptOrderNumber($site, $appId, $appSecret, $conversation, $botState);
    } else {
      $this->qApiSendMessage(
        $site,
        $appId,
        $appSecret,
        $conversation['id'],
        json_encode(array('text' => self::messages['connectToAgent']))
      );
      // TODO: Update queue
      $this->qApiSendToQueue(
        $site,
        $appId,
        $appSecret,
        $conversation['id'],
        json_encode(array('targetQueue' => 'default'))
      );
    }
  }
}
