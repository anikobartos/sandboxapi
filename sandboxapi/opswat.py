from __future__ import print_function

# import json
import sandboxapi


class OPSWATSandboxAPI(sandboxapi.SandboxAPI):
    """OPSWAT Filescan Sandbox API wrapper."""

    def __init__(self, api_key, url=None, verify_ssl=True, **kwargs):
        """
        :type   api_key:    str
        :param  api_key:    OPSWAT Filescan Sandbox API key

        :type   url         str
        :param  url         The url (including the port) of the OPSWAT Filescan Sandbox
                            instance defaults to https://www.filescan.io
        """

        """Initialize the interface to OPSWAT Filescan Sandbox API."""
        sandboxapi.SandboxAPI.__init__(self, **kwargs)
        self.api_key = api_key
        self.api_url = url or "https://www.filescan.io"
        self.headers = {"X-Api-Key": self.api_key}
        # TODO : isprivate = True ?
        self.verify_ssl = verify_ssl

    # def analyze(self, handle, filename, password = None):
    def analyze(self, handle, filename):        
        """Submit a file for analysis.

        :type  handle:   File handle
        :param handle:   Handle to file to upload for analysis.
        :type  filename: str
        :param filename: File name.

        :rtype:  str
        :return: flow_id as a string
        """

        if not self.api_key:
            raise sandboxapi.SandboxError("Missing API key")

        # multipart post files.
        files = {"file": (filename, handle)}

        # ensure the handle is at offset 0.
        handle.seek(0)

        try:
            # PASSWORD? PRIVATE? TODO
            params = {"password": "TODO" or None, "is_private": "TODO" or True}

            response = self._request(
                "/api/scan/file",
                method="POST",
                params=params,
                headers=self.headers,
                files=files,
            )

            if response.status_code == 200 and response and response.json():
                # send file, get flow_id
                if "flow_id" in response.json():
                    return response.json()["flow_id"]
            
            raise sandboxapi.SandboxError(
                "api error in analyze ({u}): {r}".format(
                    u=response.url, r=response.content
                )
            )
        except (ValueError, KeyError) as e:
            raise sandboxapi.SandboxError("error in analyze: {e}".format(e=e))

    def check(self, item_id):
        """Check if an analysis is complete.

        :type  item_id: str
        :param item_id: flow_id to check.

        :rtype:  bool
        :return: Boolean indicating if a report is done or not.
        """
        response = self._request("/api/scan/{flow_id}/report".format(flow_id=item_id))

        if response.status_code == 404:
            # unknown id
            return False

        try:
            if (
                "allFinished" not in response.json()
                and response.json()["allFinished"]
            ):
                return True

        except ValueError as e:
            raise sandboxapi.SandboxError(e)

        return False

    def is_available(self):
        """Determine if the Opswat API server is alive.

        :rtype:  bool
        :return: True if service is available, False otherwise.
        """
        # if the availability flag is raised, return True immediately.
        # NOTE: subsequent API failures will lower this flag. we do this here
        # to ensure we don't keep hitting Opswat with requests while
        # availability is there.
        if self.server_available:
            return True

        # otherwise, we have to check with the cloud.
        else:
            try:
                response = self._request("/status")

                # we've got opswat.
                if response.status_code == 200:
                    self.server_available = True
                    return True

            except sandboxapi.SandboxError:
                pass

        self.server_available = False
        return False

    def report(self, item_id, report_format="json"):
        """Retrieves the specified report for the analyzed item, referenced by item_id.

        Available formats include: json.

        :type  item_id:       str
        :param item_id:       SHA256 number
        :type  report_format: str
        :param report_format: Return format

        :rtype:  dict
        :return: Dictionary representing the JSON parsed data or raw, for other
                 formats / JSON parsing failure.
        """
        if report_format == "html":
            return "Report Unavailable"

        headers = {
            "apikey": self.api_token,
        }

        # else we try JSON
        response = self._request(
            "/sandbox/{sandbox_id}".format(sandbox_id=item_id), headers=headers
        )

        # if response is JSON, return it as an object
        try:
            return response.json()
        except ValueError:
            pass

        # otherwise, return the raw content.
        return response.content

    def score(self, report):
        """Pass in the report from self.report(), get back an int."""
        score = 0
        if report["analysis"]["infection_score"]:
            score = report["analysis"]["infection_score"]

        return score


def opswat_loop(opswat, filename):
    # test run
    with open(arg, "rb") as handle:
        sandbox_id = opswat.analyze(handle, filename)
        print(
            "file {f} submitted for analysis, id {i}".format(f=filename, i=sandbox_id)
        )

    while not opswat.check(sandbox_id):
        print("not done yet, sleeping 10 seconds...")
        time.sleep(10)

    print("analysis complete. fetching report...")
    print(opswat.report(sandbox_id))


if __name__ == "__main__":

    def usage():
        msg = "%s: apikey <submit <fh> | available | report <id> | analyze <fh>"
        print(msg % sys.argv[0])
        sys.exit(1)

    if len(sys.argv) == 2:
        cmd = sys.argv.pop().lower()
        apikey = sys.argv.pop()
        arg = None

    elif len(sys.argv) >= 3:
        arg = sys.argv.pop()
        cmd = sys.argv.pop().lower()
        apikey = sys.argv.pop()

    else:
        usage()

    # instantiate Opswat Sandbox API interface.
    opswat = OpswatAPI(apikey, "windows7")

    # process command line arguments.
    if "submit" in cmd:
        if arg is None:
            usage()
        else:
            with open(arg, "rb") as handle:
                print(opswat.analyze(handle, arg))

    elif "available" in cmd:
        print(opswat.is_available())

    elif "report" in cmd:
        if arg is None:
            usage()
        else:
            print(opswat.report(arg))

    elif "analyze" in cmd:
        if arg is None:
            usage()
        else:
            opswat_loop(opswat, arg)

    else:
        usage()
