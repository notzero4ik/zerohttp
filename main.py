from core.client import *
import sys
NOT_SET = object()
parser = argparse.ArgumentParser()
parser.add_argument("-u", "--url", required=True, help="URL to send request") 
parser.add_argument("-a", "--auth", help="Send a basic authentication form. Example: -a <username:password>")
parser.add_argument("-b", "--body", help="Payload body to send together with request. If argument is present and method is not defined, POST method will be chosen automatically.", default="")
parser.add_argument("-B", "--bearer", help="Send a bearer token for authentication.")
parser.add_argument("-c", "--content-type", help="Specify Connect-Type header")
parser.add_argument("-H", "--header", help="Adds header to the request. Example: \n-h \"Referer: https://example.com\", \"X-Forwarded-For: example.com\"\nIt is recommended to use -U for custom user-agent.", nargs="+", default=[])
parser.add_argument("-I", "--head", help="Use method HEAD.", action="store_true")
parser.add_argument("-k", "--skip-ssl", help="Skip SSL certificate check. WARNING: That makes you vulnerable to MITM attacks. Use at your own risk.", action="store_true")
parser.add_argument("-m", "--method", "-X", default=NOT_SET, help="HTTP method to use. Example: -m POST (uses POST method)")
parser.add_argument("-M", "--max-redirects", help="Sets max redirects count")
parser.add_argument("-o", "--output", help="Save output into file. Example: -o <filename>")
parser.add_argument("-oH", "--save-headers", help="Save headers into file too. Does not have effect without --output.", action="store_true")
parser.add_argument("-p", "--post", help="Change method to POST. Useful if you're too lazy to type 7 characters.", action="store_true")
parser.add_argument("-r", "--no-redirect", help="Do not follow any redirects", action="store_true")
parser.add_argument("-U", "--user-agent", help="Sets custom user-agent.", default="zerohttp/1.0")
parser.add_argument("-v", "--verbose", help="Make output more talkative", action="store_true")
		
		
def httpclient(url):
	global logger
	log_level = logging.DEBUG if args.verbose else logging.INFO
	logging.basicConfig(
        level=log_level,
        format="%(message)s",
        stream=sys.stderr
    )
	global redirect_count
	global NOT_SET
	if args.body and args.method is NOT_SET or args.post:
		args.method = "POST"
	if args.head:
		args.method = "HEAD"
	if args.method in ["POST", "PUT", "PATCH"]:
		args.header.append(f"Content-Length: {len(args.body.encode())}")
	if args.method is NOT_SET:
		args.method = "GET"
	if args.auth:
	    auth = args.auth.encode("ascii")
	    res = base64.b64encode(auth).decode('ascii')
	    args.header.append(f"Authorization: Basic {res}\r\n")
	elif args.bearer:
		args.header.append(f"Authorization: Bearer {args.bearer}\r\n")
	if args.content_type:
		args.header.append(f"Content-Type: {args.content_type}\r\n")
	args.header.append(f"User-Agent: {args.user_agent}\r\n")
	try:
		headers, data, status = send_request(args.method, url, args.body, args.header, args.skip_ssl)
	except ssl.SSLError:
		logger.error("SSL certificate check returned error! You can bypass it by adding -k option, but remember that this makes you vulnerable to MITM attacks!")
		exit()
	data = data.strip("\r\n\r\n")
	logger.debug("Response:")
	logger.debug("<--------")
	if not args.head:
		logger.info(data)
	else:
		logger.debug(headers + "\n" + data)
	if args.method == "HEAD":
		logger.info(headers)
	if args.output:
		with open(args.output, "w") as f:
			if args.save_headers:
				f.write(headers)
			f.write(data)
		logger.debug("Saved to the file " + args.output)
	if status == "301" or status == "302" or status == "307":
		if not args.no_redirect:
			if redirect_count > max_redirect:
				print("Hit max redirects count... Exiting")
				exit()
			logger.debug("Redirecting to location from response...")
			ind = headers.rfind("Location: ")
			if ind != -1:
				ind = ind + len("Location: ")
				end = headers.find("\r", ind)
				redirect_count += 1
				if end != -1:
					httpclient(headers[ind:end])
				else:
					httpclient(headers[ind:])
			else:
				logger.warn("Server returned 301 error but did not specify Location header. Not redirecting you anywhere i guess...")
	redirect_count = 0
if __name__ == "__main__":
	args = parser.parse_args()
	httpclient(args.url)
