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

variable "label" {
  description = "Labels for Charmed HPC project repositories"
  type        = list(map(string))
  default = [
    {
      name        = "backport"
      color       = "160177"
      description = "Add this label on a PR to backport its commits to our list of maintained branches"
    },
    {
      name        = "blocked"
      color       = "57006f"
      description = "A dependency must be resolved before this is actionable"
    },
    {
      name        = "C-filesystem"
      color       = "a54a05"
      description = "Component: Filesystem"
    },
    {
      name        = "C-idm"
      color       = "a54a06"
      description = "Component: Identity Management"
    },
    {
      name        = "C-slurm"
      color       = "a54a04"
      description = "Component: Slurm"
    },
    {
      name        = "C-terraform"
      color       = "a54a07"
      description = "Component: Terraform/OpenTofu"
    },
    {
      name        = "cleanup"
      color       = "16cc3b"
      description = "This pull request cleans up the project and introduces no functional changes"
    },
    {
      name        = "confirmed"
      color       = "99eac1"
      description = "This issue was successfully reproduced during triage"
    },
    {
      name        = "docs"
      color       = "2f7cdc"
      description = "This pull request makes a change to the documentation"
    },
    {
      name        = "feature"
      color       = "466334"
      description = "This pull request adds a new feature to the project"
    },
    {
      name        = "fix"
      color       = "ca299e"
      description = "This pull request fixes a confirmed issue"
    },
    {
      name        = "good first issue"
      color       = "7ff5e8"
      description = "Good first issue for project newcomers"
    },
    {
      name        = "help wanted"
      color       = "afddc7"
      description = "This issue needs an assignee"
    },
    {
      name        = "needs testing"
      color       = "18ef6b"
      description = "This pull request needs additional tests added before it is eligible for merge"
    },
    {
      name        = "needs triage"
      color       = "b04642"
      description = "Reported issue needs to be confirmed the triage"
    },
    {
      name        = "P-critical"
      color       = "c70c78"
      description = "Priority: Issue needs addressed as soon as possible"
    },
    {
      name        = "P-high"
      color       = "c65103"
      description = "Priority: Issue needs addressed within a two week pulse"
    },
    {
      name        = "P-low"
      color       = "a0cab4"
      description = "Priority: Issue should be addressed within a six month cycle"
    },
    {
      name        = "P-medium"
      color       = "3df315"
      description = "Priority: Issue needs addressed within a month"
    },
    {
      name        = "R-cannot-reproduce"
      color       = "dc9b13"
      description = "Resolution: This issue could not be reproduced during triage"
    },
    {
      name        = "R-duplicate"
      color       = "dc9b13"
      description = "Resolution: This issue or pull request is a duplicate"
    },
    {
      name        = "R-needs-more-info"
      color       = "dc9b11"
      description = "Resolution: This issue needs additional information provided before triage can continue"
    },
    {
      name        = "R-out-of-scope"
      color       = "dc9b12"
      description = "Resolution: This issue or pull request is out-of-scope for project"
    },
    {
      name        = "waiting for author"
      color       = "7498c0"
      description = "This issue or pull request is waiting for the author(s) to comment"
    },
    {
      name        = "waiting for reviewer"
      color       = "7498c0"
      description = "This issue or pull request is waiting for the reviewer(s) to comment"
    },
    {
      name        = "ux"
      color       = "3b33d1"
      description = "This pull request changes the user experience of the project"
    },
    {
      name        = "Charmed HPC 2026.1"
      color       = "ccedc7"
      description = "The resolution for this issue will be included in Charmed HPC 2026.1"
    },
    {
      name        = "Charmed Slurm 25.11"
      color       = "ccedc7"
      description = "The resolution for this issue will be included in Charmed Slurm 25.11"
    }
  ]
}

variable "repository" {
  description = "List of Charmed HPC repositories to apply labels to"
  type        = set(string)
  default = [
    "apptainer-operator",
    "charmed-hpc-benchmarks",
    "charmed-hpc-docs",
    "charmed-hpc-libs",
    "charmed-hpc-terraform",
    "filesystem-charms",
    "gherkinator",
    "hpc-specs",
    "hpc-team",
    "ondemand-snap",
    "openssh-operator",
    "pytest-jubilant-bdd",
    "slurm-charms",
    "slurm-snap",
    "slurmutils",
    "sssd-operator",
  ]
}
