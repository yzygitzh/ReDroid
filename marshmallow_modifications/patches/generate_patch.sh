#!/bin/bash

# patch storage folder
PATCH_DIR="/mnt/EXT_volume/projects_light/ReDroid/marshmallow_modifications/patches"

# AOSP project name
AOSP_NAME="aosp"
# AOSP folder path
AOSP_ROOT="/mnt/EXT_volume/projects_large/aosp/aosp-latest/aosp"
# modified AOSP project path
AOSP_PROJECTS=(
    "build/"
    "frameworks/base/"
    "system/core/"
    "art/"
)
# AOSP branch name
AOSP_OLD_BRANCH="android-6.0.1_r77"
AOSP_NEW_BRANCH="android-6.0.1_r77_anti-sandbox"

# Android-x86 project name
ANDX86_NAME="android-x86"
# Android-x86 folder path
ANDX86_ROOT="/mnt/EXT_volume/projects_large/aosp/android-x86"
# modified Android-x86 project path
ANDX86_PROJECTS=(
    "bootable/newinstaller/"
    "build/"
    "device/generic/common/"
    "external/mesa/"
    "frameworks/base/"
)
# Android-x86 branch name
ANDX86_OLD_BRANCH="remotes/m/android-x86-6.0-r3"
ANDX86_NEW_BRANCH="android-x86-6.0-r3-anti-sandbox"

# gen_patch
# args:
# project_name project_root subproject_dir old_branch_name new_branch_name
gen_patch () {
    cd "$2/$3"
    git checkout $4
    git checkout -b anti-sandbox-patch
    git merge $5 --squash
    git add -all .
    git commit -m "anti sandbox patch"
    git format-patch $4
    git checkout $5
    git branch -D anti-sandbox-patch
    mkdir -p "$PATCH_DIR/$1/$3"
    mv 000* "$PATCH_DIR/$1/$3/"
}

rm -rf "$PATCH_DIR/$AOSP_NAME"
rm -rf "$PATCH_DIR/$ANDX86_NAME"

for AOSP_PROJECT in "${AOSP_PROJECTS[@]}"; do
    gen_patch $AOSP_NAME $AOSP_ROOT $AOSP_PROJECT $AOSP_OLD_BRANCH $AOSP_NEW_BRANCH
done

for ANDX86_PROJECT in "${ANDX86_PROJECTS[@]}"; do
    gen_patch $ANDX86_NAME $ANDX86_ROOT $ANDX86_PROJECT $ANDX86_OLD_BRANCH $ANDX86_NEW_BRANCH
done
