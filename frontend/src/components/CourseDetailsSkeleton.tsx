import React from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const CourseDetailsSkeleton: React.FC = () => (
  <Card className="mt-6 animate-pulse">
    {" "}
    <CardHeader>
      {/* Skeleton for Course Title */}
      <Skeleton className="h-7 w-3/5 mb-2 rounded" />
      {/* Skeleton for Course Description */}
      <Skeleton className="h-4 w-4/5 rounded" />
    </CardHeader>
    <CardContent className="space-y-6">
      {/* Skeleton for a single Section Block (e.g., LEC) */}
      <div>
        {/* Skeleton for Block Title (e.g., "LEC Sections") */}
        <Skeleton className="h-6 w-1/4 mb-3 rounded" />
        <Table>
          <TableHeader>
            <TableRow>
              {/* Mimic Table Head widths */}
              <TableHead className="w-[100px]">
                <Skeleton className="h-4 w-16 rounded" />
              </TableHead>
              <TableHead className="w-[120px]">
                <Skeleton className="h-4 w-20 rounded" />
              </TableHead>
              <TableHead className="text-center w-[140px]">
                <Skeleton className="h-4 w-24 mx-auto rounded" />
              </TableHead>
              <TableHead className="text-right w-[80px]">
                <Skeleton className="h-4 w-12 ml-auto rounded" />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {/* Render a few representative skeleton rows */}
            {[1, 2, 3].map((j) => (
              <TableRow key={`skeleton-row-${j}`}>
                {/* Section Name Cell - Varying width */}
                <TableCell>
                  <Skeleton
                    className={`h-5 w-${j === 2 ? "10/12" : "full"} rounded`}
                  />
                </TableCell>
                {/* Section Key Cell - Varying width */}
                <TableCell>
                  <Skeleton
                    className={`h-5 w-${j === 1 ? "11/12" : "full"} rounded`}
                  />
                </TableCell>
                {/* Availability Text Cell */}
                <TableCell className="text-center">
                  <Skeleton className="h-5 w-20 mx-auto rounded-md" />
                </TableCell>
                {/* Watch Button Cell */}
                <TableCell className="text-right">
                  <Skeleton className="h-8 w-8 ml-auto rounded" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Skeleton className="h-px w-full my-6" />
      <div>
        <Skeleton className="h-6 w-1/5 mb-3 rounded" />
        <Skeleton className="h-10 w-full rounded" />
      </div>
    </CardContent>
    <CardFooter>
      {/* Skeleton for Footer Text */}
      <Skeleton className="h-4 w-3/4 rounded" />
    </CardFooter>
  </Card>
);

// Use default export convention
export default CourseDetailsSkeleton;