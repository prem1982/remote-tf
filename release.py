#!/usr/bin/env python

import argparse
import os

from git import Repo
import semantic_version


class Scope:
    Major = "major"
    Minor = "minor"
    Patch = "patch"


class WorkingRepo:
    Master_Branch = "master"

    def __init__(self, scope, repo_dir=None):

        if repo_dir is None:
            self.repo = Repo(os.getcwd())
        else:
            self.repo = Repo(repo_dir)
        self.scope = scope

    def check_okay_repo_status(self):
        dirty = self.repo.is_dirty()
        any_untracked = len(self.repo.untracked_files)
        status = not dirty and not any_untracked

        return status

    def check_allowed_branch(self):
        return self.repo.active_branch.name == WorkingRepo.Master_Branch

    def get_tags(self):
        return self.repo.tags

    def create(self):

        tags = self.get_tags()

        version = "0.0.1"
        if len(tags) == 0:
            version = "0.0.1"
        else:

            latest_tag = tags[-1]
            v = semantic_version.Version(latest_tag.name)

            if self.scope == Scope.Major:
                version = str(v.next_major())

            if self.scope == Scope.Minor:
                version = str(v.next_minor())
            if self.scope == Scope.Patch:
                version = str(v.next_patch())

        annotated_tag = "v{version}: Release of {version}".format(version=version)

        print annotated_tag
        new_tag = self.repo.create_tag(version, message=annotated_tag)
        self.repo.remotes.origin.push(new_tag)

    def release(self):

        if self.check_okay_repo_status() and self.check_allowed_branch():
            self.create()
        else:
            raise ValueError("Check Repo status or branch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Release Application')
    parser.add_argument('--scope', action="store", dest="scope", default=Scope.Patch)
    args = parser.parse_args()
    repo = WorkingRepo(args.scope)
    repo.release()
