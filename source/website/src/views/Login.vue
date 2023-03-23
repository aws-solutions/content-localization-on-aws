<!-- 
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
-->
<template>
  <div>
    <amplify-authenticator></amplify-authenticator>
  </div>
</template>

<script>
import { AmplifyEventBus } from "aws-amplify-vue";

export default {
  name: "Login",
  data() {
    return {};
  },
  mounted() {
    AmplifyEventBus.$on("authState", eventInfo => {
      if (eventInfo === "signedIn") {
        this.$router.push({ name: "collection" });
      } else if (eventInfo === "signedOut") {
        this.$router.push({ name: "Login" });
      }
    });
  },
  created() {
    this.getLoginStatus()
  },
  methods: {
    getLoginStatus () {
      this.$Amplify.Auth.currentSession().then(data => {
        this.session = data;
        if (this.session == null) {
          console.log('user must login')
        } else {
          this.$router.push({name: "collection"})
        }
      })
    }
  }
};
</script>
