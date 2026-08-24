#!/usr/bin/env just --justfile
# Copyright 2025-2026 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Necessary to use `||` logical operator.
set unstable
set lists

terraform_dir := justfile_dir() + "/terraform/"
default_plan_list := shell("ls -d -- $1/*", terraform_dir)

[private]
default:
    @just help

# Prepare the local environment
setup: init

# Clean project directory
clean:
    find . -name .terraform -type d | xargs rm -rf
    find . -name .terraform.lock.hcl -type f | xargs rm -rf
    find . -name "terraform.tfstate*" -type f | xargs rm -rf

# Apply static checks
check: fmt validate

# Run tests for specified targets, or all tests if none specified
test *targets:
    @echo "No tests to run"

# Apply formatting standards to project
fmt:
    just --fmt --unstable
    tofu fmt -recursive

# Initialize Terraform plans
init *plans:
    #!/usr/bin/env bash
    set -euxo pipefail
    plans=({{ prepend(terraform_dir, plans) || default_plan_list }})
    for plan in ${plans[@]}; do
        tofu -chdir=${plan} init
    done

# Validate Terraform plans
validate *plans: (init plans)
    #!/usr/bin/env bash
    set -euxo pipefail
    plans=({{ prepend(terraform_dir, plans) || default_plan_list }})
    for plan in ${plans}; do
        tofu -chdir=${plan} fmt -check
        tofu -chdir=${plan} validate
    done

# Apply Terraform plans
apply *plans: (validate plans)
    #!/usr/bin/env bash
    set -euxo pipefail
    plans=({{ prepend(terraform_dir, plans) || default_plan_list }})
    for plan in ${plans[@]}; do
        tofu -chdir=${plan} plan
        GITHUB_TOKEN=${CHARMED_HPC_ORG_PAT} tofu -chdir=${plan} apply -auto-approve
    done

# Show available recipes
help:
    @just --list --unsorted
