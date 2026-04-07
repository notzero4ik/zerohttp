import socket
import argparse
import ssl
import base64
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
args = parser.parse_args()
HTTP_VERSION = "1.1"
ENCODING = "text/html"

verboselog = lambda msg: print(msg) if args.verbose else None
max_redirect = 5
redirect_count = 0

def form_request(method, host, path, body):

	request = (
        f"{method} {path} HTTP/{HTTP_VERSION}\r\n"
        f"Host: {host}\r\n"
        f"User-Agent: {args.user_agent}\r\n"
        f"Accept: {ENCODING}\r\n"
        f"Connection: close\r\n"
    )
	for i in args.header:
	    request += i 
	    request += "\r\n"
	if args.auth:
	    auth = args.auth.encode("ascii")
	    res = base64.b64encode(auth).decode('ascii')
	    request += f"Authorization: Basic {res}\r\n"
	elif args.bearer:
		request += f"Authorization: Bearer {args.bearer}\r\n"
	if args.content_type:
		request += f"Content-Type: {args.content_type}\r\n"
	request += "\r\n"
	request += f"{body}"
	#print(request)
	return request

def split_url(url):
	url = url.split("://")
	proto = url[0]
	port = 80
	path = "/"
	if proto == "https":
		port = 443
	ind = url[1].find("/")
	if ind != -1:
		host = url[1][:ind]
		path = url[1][ind:]
	else:
		host = url[1]
	return proto,host,path,port

def send_request(method, url):
	proto, host, path, port = split_url(url)
	#print(proto,host,path,port)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((host, port))
	
	verboselog(f"Connected to {host}:{port}")
	if proto == "https":
		if args.skip_ssl:
			context = ssl._create_unverified_context()
			s = context.wrap_socket(s, server_hostname=host)
		else: 
			try:
				context = ssl.create_default_context()
				s = context.wrap_socket(s, server_hostname=host)
			except:
				print("Failed to verify SSL  certificate (hostname mismatch). If you think this is a mistake, use -k, but remember that this makes you vulnerable to traffic intercepting and MITM attacks!")
				exit()
		
		verboselog("Using HTTPS")
	request = form_request(method, host, path, args.body)
	verboselog(("Request:\n"
		"-------->"
	))
	verboselog(request)
	s.sendall(request.encode("utf-8"))
	response = b""
	while True:
		data = s.recv(1024)
		if not data:
		  	break
		response += data
	return response.decode()
   
def handle_response(response):
	ind = response.find("\r\n\r\n")
	headers, data = response.split("\r\n\r\n")[0], response[ind:]
	
	return headers, data, headers.split()[1]
def get(url):
	response = send_request("GET", url)
	headers, data, status = handle_response(response)
	return headers, data, status


def post(url):
	response = send_request("POST", url)
	headers, data, status = handle_response(response)
	return headers, data, status
	
def put(url):
	response = send_request("PUT", url)
	headers, data, status = handle_response(response)
	return headers, data, status
	
def patch(url):
	response = send_request("PATCH", url)
	headers, data, status = handle_response(response)
	return headers, data, status
	
def delete(url):
	response = send_request("DELETE", url)
	headers, data, status = handle_response(response)
	return headers, data, status
	
def head(url):
	response = send_request("HEAD", url)
	headers, data, status = handle_response(response)
	return headers, data, status
	
def httpclient(url):
	global redirect_count
	global NOT_SET
	if args.body and args.method is NOT_SET or args.post:
		args.method = "POST"
	if args.head:
		args.method = "HEAD"
	match args.method:
		case "GET":
			headers, data, status = get(url)
		case "POST":
			args.header.append(f"Content-Length: {len(args.body.encode())}")
			headers, data, status = post(url)
		case "PUT":
			args.header.append(f"Content-Length: {len(args.body.encode())}")
			headers, data, status = put(url)
		case "PATCH":
			args.header.append(f"Content-Length: {len(args.body.encode())}")
			headers, data, status = patch(url)
		case "DELETE":
			headers, data, status = delete(url)
		case "HEAD":
			headers, data, status = head(url)
		case NOT_SET:
			headers, data, status = get(url)
	data = data.strip("\r\n\r\n")
	if args.verbose:
		print("Response:")
		print("<--------")
		print(headers, "\n", data)
	else:
		print(data)
	if args.output:
		with open(args.output, "w") as f:
			if args.save_headers:
				f.write(headers)
			f.write(data)
	if status == "301" or status == "302" or status == "307":
		if not args.no_redirect:
			if redirects_count > max_redirect:
				print("Hit max redirects count... Exiting")
				exit()
			verboselog("Redirecting to location from response...")
			ind = headers.rfind("Location: ")
			if ind != -1:
				ind = ind + len("Location: ")
				end = headers.find("\r", ind)
				redirect_count += 1
				if end != -1:
					httpclient(headers[ind:end])
				else:
					httpclient(headers[ind:])
	redirect_count = 0
httpclient(args.url)