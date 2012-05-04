<!doctype html>
<html>
	<head>
		<title>Cryto Tahoe-LAFS Storage Grid repair utility</title>
		<style>
			pre
			{
				max-height: 300px;
				overflow: auto;
				background-color: #E7E7E7;
				padding: 12px;
			}
		</style>
	</head>
	<body>
		<?php

		function curl_post($url, $variables)
		{
			if(is_array($variables))
			{
				foreach($variables as $key => $value)
				{
					$variables[$key] = urlencode($value);
					$variable_strings[] = "{$key}={$value}";
				}
				
				$post_string = implode("&", $variable_strings);
			}
			else
			{
				$post_string = "";
			}
			
			$ch = curl_init();
			curl_setopt($ch, CURLOPT_URL, $url);
			curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
			curl_setopt($ch, CURLOPT_POST, count($variables));
			curl_setopt($ch, CURLOPT_POSTFIELDS, $post_string);
			
			$result = curl_exec($ch);
			
			$error = curl_error($ch);
			if(empty($error))
			{
				$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
				$return_object->result = $result;
				$return_object->code = $code;
				return $return_object;
			}
			else
			{
				return false;
			}
			
			curl_close($ch);
		}

		if(isset($_POST['submit']))
		{
			$uri = $_POST['uri'];
			$process = true;
			
			// process repair request
			if(preg_match("/http:\/\/[^\/]+\/download\/([^\/]+)(\/.*)?/i", $uri, $matches))
			{
				// gateway url
				$uri = $matches[1];
			}
			
			if(!preg_match("/^[a-zA-Z0-9=_:]+$/i", $uri))
			{
				$process = false;
				echo("ERROR: Your input was in an invalid format.<br><br>");
			}
			
			if(strpos($uri, ":") === false)
			{
				// probably base64
				$uri = base64_decode($uri);
				
				if($uri === false)
				{
					$process = false;
					echo("ERROR: Your input was invalid. Check if it's really a valid Tahoe-LAFS gateway URL, base64-encoded URI, or plaintext URI.<br><br>");
				}
			}
			
			if($process === true)
			{
				$result = curl_post("http://localhost:3456/uri/{$uri}?t=check&repair=true&output=json", false);
				
				if($result->code == 200)
				{
					$result_object = json_decode($result->result);
					
					$attempted = $result_object->{'repair-attempted'};
					
					if($attempted)
					{
						$succeeded = $result_object->{'repair-successful'};
					}
					else
					{
						$succeeded = false;
					}
					
					if($attempted === false)
					{
						echo("<strong>The file is still healthy, and does not need to be repaired.</strong>");
					}
					elseif($attempted === true && $succeeded === false)
					{
						echo("<strong>Repair of the file was attempted, but FAILED.</strong>");
					}
					else
					{
						echo("<strong>Repair of the file was SUCCESSFULLY completed.</strong>");
					}
					
					echo("<pre>{$result->result}</pre>");
				}
				else
				{
					echo("ERROR: Repair failed. Your input may be in the wrong format or the server may be down.<br><br>");
				}
			}
		}
		?>

		<form method="post" action="repair.php">
			URI/base64/URL: <input type="text" name="uri">
			<button type="submit" name="submit" value="submit">Repair!</button>
		</form>
	</body>
</html>