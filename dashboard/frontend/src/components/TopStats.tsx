import { Flame, Trophy, Users } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import type { DbTop } from "@/utils/api";

interface TopStatsProps {
  top: DbTop | null;
}

export const TopStats: React.FC<TopStatsProps> = ({ top }) => {
  if (!top) {
    return (
      <Card className="bg-card/40 backdrop-blur-sm">
        <CardContent className="flex flex-col gap-4 py-6">
          <Skeleton className="h-4 w-40" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/40 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-sm font-bold tracking-tight">Top Courses & Users</CardTitle>
        <CardDescription>Demand and seat-opening leaders, last 7 days</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="watched">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="watched">
              <Trophy className="h-3.5 w-3.5" />
              Most Watched
            </TabsTrigger>
            <TabsTrigger value="openings">
              <Flame className="h-3.5 w-3.5" />
              Seat Openings
            </TabsTrigger>
            <TabsTrigger value="users">
              <Users className="h-3.5 w-3.5" />
              Top Users
            </TabsTrigger>
          </TabsList>

          <TabsContent value="watched" className="mt-4">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>#</TableHead>
                  <TableHead>Course</TableHead>
                  <TableHead className="text-right">Watches</TableHead>
                  <TableHead className="text-right">Users</TableHead>
                  <TableHead className="text-right">Notified</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {top.top_courses.map((course, i) => (
                  <TableRow key={course.course_code}>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {i + 1}
                    </TableCell>
                    <TableCell className="font-semibold">{course.course_code}</TableCell>
                    <TableCell className="text-right font-mono text-sm font-bold">
                      {course.watch_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {course.users}
                    </TableCell>
                    <TableCell className="text-right text-green-400">{course.notified}</TableCell>
                  </TableRow>
                ))}
                {top.top_courses.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="h-16 text-center text-sm text-muted-foreground"
                    >
                      No watch data yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TabsContent>

          <TabsContent value="openings" className="mt-4">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>#</TableHead>
                  <TableHead>Course</TableHead>
                  <TableHead className="text-right">Seat openings (7d)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {top.top_openings.map((course, i) => (
                  <TableRow key={course.course_code}>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {i + 1}
                    </TableCell>
                    <TableCell className="font-semibold">{course.course_code}</TableCell>
                    <TableCell className="text-right font-mono text-sm font-bold text-green-400">
                      {course.openings.toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
                {top.top_openings.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={3}
                      className="h-16 text-center text-sm text-muted-foreground"
                    >
                      No seat openings recorded in the last 7 days.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TabsContent>

          <TabsContent value="users" className="mt-4">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>#</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead className="text-right">Watches</TableHead>
                  <TableHead className="text-right">Notified</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {top.top_users.map((user, i) => (
                  <TableRow key={user.email}>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {i + 1}
                    </TableCell>
                    <TableCell className="max-w-[260px] truncate text-muted-foreground">
                      {user.email}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm font-bold">
                      {user.watch_count.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right text-green-400">{user.notified}</TableCell>
                  </TableRow>
                ))}
                {top.top_users.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={4}
                      className="h-16 text-center text-sm text-muted-foreground"
                    >
                      No users yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};

export default TopStats;
