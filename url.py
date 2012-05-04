import sys,base64

if len(sys.argv) < 3:
	print ("""\
	Usage: url.py cap filename
	cap = Tahoe-LAFS readcap
	filename = Actual filename of the file
	""")
else:
	print "http://tahoe-gateway.cryto.net:3719/download/" + base64.urlsafe_b64encode(sys.argv[1]) + "/" + sys.argv[2]
