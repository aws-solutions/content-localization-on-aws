/*
######################################################################################################################
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.                                                #
#                                                                                                                    #
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
#  with the License. A copy of the License is located at                                                             #
#                                                                                                                    #
#      http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                    #
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    #
#  and limitations under the License.                                                                                #
######################################################################################################################
*/

import axios from "axios";

export default {
  getSignedURL(file, config) {
    return new Promise((resolve, reject) => {
      const token = config.token;
      let request = new XMLHttpRequest(),
          signingURL = (typeof config.signingURL === "function") ?  config.signingURL(file) : config.signingURL;
      // console.log('signing URL: ', signingURL)
      request.open("POST", signingURL);
      request.setRequestHeader("Content-Type", "application/json");
      request.setRequestHeader("Authorization", token);
      // console.log(token)
      request.onload = function () {
        if (request.status === 200) {
          resolve(JSON.parse(request.response));
        } else {
          reject((request.statusText));
        }
      };
      request.onerror = function (err) {
        console.error("Network Error : Could not send request to AWS (Maybe CORS errors)");
        reject(err)
      };
      if (config.withCredentials === true) {
        request.withCredentials = true;
      }
      axios.get('/runtimeConfig.json').then(response => {
        request.send("{\"S3Bucket\":\""+response.data.DATAPLANE_BUCKET+"\",\"S3Key\":\""+file.name+"\"}");
      })
    });
  },
  sendFile(file, config) {
    return this.getSignedURL(file, config)
      .then((response) => {return ({'success': true, 'message': response})});
  },
}
