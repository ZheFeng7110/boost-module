/*
 *          Copyright Andrey Semashev 2007 - 2015.
 * Distributed under the Boost Software License, Version 1.0.
 *    (See accompanying file LICENSE_1_0.txt or copy at
 *          http://www.boost.org/LICENSE_1_0.txt)
 */

/*
 * M11: hand-written replacement for the mc.exe-generated header. Upstream
 * builds it from simple_event_log.mc at configure/build time (see
 * libs/log/CMakeLists.txt); the vendored tree has no build-time code
 * generation, so the constants (which only need to be self-consistent event
 * IDs passed to ReportEvent) are defined here directly, mirroring the .mc
 * MessageId/Severity layout.
 */

#pragma once

#define BOOST_LOG_SEVERITY_DEBUG   0x00000000L
#define BOOST_LOG_SEVERITY_INFO    0x00000001L
#define BOOST_LOG_SEVERITY_WARNING 0x00000002L
#define BOOST_LOG_SEVERITY_ERROR   0x00000003L

#define BOOST_LOG_MSG_DEBUG   ((DWORD)0x01000100L)
#define BOOST_LOG_MSG_INFO    ((DWORD)0x01000101L)
#define BOOST_LOG_MSG_WARNING ((DWORD)0x01000102L)
#define BOOST_LOG_MSG_ERROR   ((DWORD)0x01000103L)
